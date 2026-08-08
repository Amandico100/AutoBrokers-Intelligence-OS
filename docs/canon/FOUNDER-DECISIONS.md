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

---

## D16 — Firecrawl como capacidade governada e medida

**Data:** 25/07/2026 · **Estado:** AUTORIZADA pelo Founder · **Origem:** Founder

### O que foi decidido

Firecrawl entra como **capacidade da plataforma** (AutoBrokers paga a chave),
com consumo medido por corretora desde o primeiro dia.

### O que NÃO foi feito, e por quê

Não foi criada uma segunda busca na web. `platform.web.search` já existe e usa
Tavily; duplicá-la seria o motor paralelo que o CLAUDE.md §5 proíbe. O que
entrou é uma capacidade que **não existia**: `platform.web.scrape` — ler uma
página inteira resolvendo JavaScript, e ler um documento público como texto.

### Medição

Todo consumo emite `usage_event` com `unit_kind='firecrawl_credit'`, nascendo
`PRE_LAUNCH_NON_BILLABLE` como todo o resto (SPEC-055). **Mede, não cobra.**
O rating comercial continua sendo da SPEC-062 — e quando ligar, o histórico já
estará atribuído por corretora.

O crédito reportado pela própria API é sempre preferido à estimativa. Quando só
há estimativa, o evento é marcado como tal: número inventado que se apresenta
como medido é pior do que número ausente, porque vira fatura.

### Segurança da chave — PENDÊNCIA ABERTA

A chave foi transmitida por chat e apareceu em captura de tela. Não foi gravada
em arquivo, commit, log ou documentação — entra apenas como variável de
ambiente. **Deve ser rotacionada** assim que o sistema estiver rodando: gerar
nova no painel, trocar a variável, revogar a atual. Registrado junto do D12.

### Limite deliberado

Atendimento **não** recebe leitura profunda. O agente que fala com o segurado
no WhatsApp não tem por que abrir páginas arbitrárias da internet — a SPEC-054
já tirou dele o HTTP genérico pelo mesmo motivo.

---

## D17 — Corpus normativo: ler uma vez, servir a todas

**Data:** 25/07/2026 · **Estado:** AUTORIZADA pelo Founder · **Origem:** Founder

### A proposta do Founder

> "TODAS AS CONDIÇÕES GERAIS SÃO AS MESMAS PARA TODAS AS CORRETORAS, TODOS OS
> SEGURADOS. ENTÃO NÃO TEM SENTIDO IR SEMPRE LÁ BUSCAR A INFORMAÇÃO QUE
> PODERÍAMOS COLOCAR NAS MEMÓRIAS/RAG."

### Avaliação do Executor: correta, e por uma razão a mais

Custo é o argumento óbvio e ele procede. O argumento mais forte é **consistência**:
se duas corretoras perguntarem a mesma coisa sobre a mesma apólice e receberem
respostas diferentes porque o PDF foi lido em dias diferentes, isso não é
desperdício — é **erro**. Documento normativo tem de dar a mesma resposta para
todo mundo.

### O que impede isto de virar passivo

Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não
pela de hoje. Um cache que guarda "a condição atual" e responde sobre apólice
antiga pode estar confiantemente errado sobre cobertura — e o corretor repete
isso ao cliente.

Por isso o catálogo guarda **número de processo SUSEP** (a identidade legal),
**vigência** e histórico de versões; e o cabeçalho de procedência entra
**dentro** do texto ingerido, para que qualquer trecho recuperado carregue a
seguradora, o ramo e a vigência junto.

### Nenhuma estrutura paralela

A coleção Qdrant global, o serviço de busca e a `knowledge.global.search` já
existiam. Foi criado apenas o **catálogo**. A ingestão usa as mesmas primitivas
do `global_knowledge_seed` (mesma coleção, mesmo escopo, mesmo serviço Qdrant),
mudando só o `namespace` de `canon` para `normative`. A reconferência periódica
entra no laço de manutenção do worker da SPEC-055 — nenhum agendador novo.

### Curadoria é humana

Descoberta automática **propõe**; `approved_at` libera. Documento normativo
alimenta o cérebro de todas as corretoras — isso não se decide por acaso de
navegação. O worker só ingere o que foi aprovado.

### Custo

A leitura é da **plataforma**, não da corretora que porventura disparou. Cobrar
da primeira corretora a leitura de um documento que serve a todas seria cobrar
quem chegou primeiro.

---

## D18 — Corpus normativo pausado por crédito do Firecrawl

**Data:** 26/07/2026 · **Estado:** BLOQUEIO ATIVO — aguardando ação do Founder
**Origem:** Founder · **Afeta:** SPEC-057 Bloco H

### Situação

O corpus normativo **funcionou e está parcialmente populado**:

| | |
|---|---:|
| Documentos ingeridos | **8** |
| Chunks no conhecimento global | **3.744** |
| Bradesco | 5 docs · 2.632 chunks |
| Mapfre | 3 docs · 1.112 chunks |
| **Na fila, aguardando crédito** | **23** |

Os 23 restantes falharam com **HTTP 402 (Payment Required)**: o plano gratuito
do Firecrawl esgotou os créditos após ~13 leituras.

### Decisão do Founder

> "NAO POSSO FAZER O UPGRADE DO PLANO AGORA. ENTAO DEVE CONTINUAR NA FILA ATÉ EU
> FAZER ESSE UPGRADE."

**Não fazer upgrade agora.** A fila permanece e retoma sozinha.

### O que já está garantido no código

- `HTTP 402` **não gasta tentativa** e **não** marca o documento como
  `unreachable`. Sem isso o corpus desistiria de documentos válidos por causa
  da fatura, e ninguém descobriria o motivo real depois.
- Reagenda para **6 horas** e **para o ciclo** — insistir só produz mais 402.
- O worker retoma **sozinho** no primeiro ciclo de manutenção após haver
  crédito. **Nenhuma ação de código é necessária.**

### Quando o Founder fizer o upgrade

Nada a executar. O worker detecta no próximo ciclo (a cada 5 minutos) e
continua de onde parou, 3 documentos por vez.

Para conferir o andamento:

```sql
select status, count(*) from normative_documents group by status;
select count(*) filter (where status='ingested') ingeridos,
       sum(chunk_count) chunks from normative_documents;
```

### O que NÃO fazer

- **Não** trocar de provedor para contornar o limite. O Firecrawl está
  governado, medido e com allowlist de egresso; um contorno seria motor
  paralelo (CLAUDE.md §5).
- **Não** marcar os 23 documentos como rejeitados. Eles estão corretos e
  verificados — o que falta é crédito, não qualidade.

---

## D19 — Instalação guiada do Auxiliar fica pendente

**Data:** 26/07/2026 · **Estado:** PENDENTE por decisão conjunta
**Origem:** Founder + Executor · **Afeta:** SPEC-058

### O que ficou de fora

O fluxo em que o **corretor aceita a proposta pela tela** e o Auxiliar é de
fato instalado: revisão registrada, checagem de dependências ("falta conectar
o WhatsApp") e botão de desligar.

### O que JÁ existe

- Schema completo: `tenant_auxiliary_revisions`, `auxiliary_events`,
  `auxiliary_template_releases`
- O chat **propõe** o formato certo (`avaliar_automacao`)
- O Admin **vê** catálogo, instalações, saúde e oportunidades

Falta apenas o corretor **aceitar por conta própria**.

### Decisão

> Founder: "SE FOR DEMORAR MUITO PODEMOS FAZER DEPOIS FOCADOS EXATAMENTE NISSO.
> MAS NAO QUERO PICOTAR MAIS AS EXECUÇÕES."

Merece execução dedicada, não um pedaço no fim de outra SPEC. Retomar quando o
Founder indicar — sugestão do Executor: **depois da SPEC-061** (Control Plane),
que traz o restante das superfícies de administração.

---

## D20 — O motor de agentes não vai para a mão da corretora

**27/07/2026** · SPEC-061 §6 · commit `0eb903b`

A SPEC-061 §6 manda tirar cinco telas do `/admin`. O Executor moveu as cinco
para a raiz do `/dashboard` sem ver que quatro delas **já tinham casa** em
`/dashboard/personalizacao`, desde a SPEC-045. Resultado: duas telas para cada
coisa, e a que ficou visível era a crua do admin.

A tela de agentes movida trazia **"Criar Novo Agente"** e uma **lixeira**. A
lixeira apagava `autobrokers-sandbox` — o agente ATIVO que **é** o chat da
corretora. Um corretor curioso desligaria o próprio produto sem entender.

### Decisão

> Founder: "NOSSA PROPOSTA NAO É TER UMA ESTRUTURA DE CRIAÇÃO DE AGENTES PARA AS
> CORRETORAS, PELO MENOS POR ENQUANTO. ELE NAO VAI SABER FAZER. CAPAZ DE FAZER
> MERDA AINDA."

O motor de construir agentes, subagentes, `tools_config` e temperatura fica na
plataforma, em `/admin/companies/<id>/agents`, onde já estava. A corretora vê
apenas o que é dela, em Personalização, com linguagem de gente.

Isto **não** reverte a §6: `/admin` continua sendo só da plataforma. O que se
desfaz é a duplicação, não a separação.

### Regra que fica

**O menu do `/dashboard` não cresce.** Coisa nova entra DENTRO de um item que
já existe. Se não couber em nenhum, o desenho dos itens é que está errado — não
falta um item. Registrado em `lib/navigation.ts` e cobrado por SEP-01.

---

## D21 — Nenhum consumo anterior ao lançamento comercial vira cobrança

**27/07/2026** · SPEC-062 §22 · commits `f38369b`, `0eb903b`

Existem **1.239 linhas** em `token_usage_logs` com `billed = false` — o registro
técnico de um ano de desenvolvimento e teste. O worker legado
`process_unbilled_usage` busca exatamente esse estado e **debita crédito**.

O que separava as corretoras de um débito retroativo de um ano era
`USE_CELERY=false`. Uma variável de ambiente. Não é proteção; é sorte.

E a **AutoFleet estava sem serviço**: empresa ativa, sem linha em
`company_credits`, saldo lido como zero, HTTP 402 no chat e nos auxiliares.
Ninguém decidiu bloqueá-la — o bloqueio foi a ausência de uma linha numa tabela.
Com dado real, a regra antiga barrava **3 das 5 empresas**.

### Decisão

> Founder: "PRECISAMOS DEIXAR TUDO DESLIGADO AINDA ESSA PARTE DE COBRANÇA. AS
> CORRETORAS QUE TEM NO SISTEMA ATÉ AGORA NAO PODEM SER TRAVADAS POR CAUSA DOS
> TOKENS OU PLANOS." · "TODO O CUSTO RETROATIVO NAO VAI SER COBRADO."

Duas travas, ambas com padrão que protege:

| Variável | Ausente significa | Efeito |
|---|---|---|
| `BILLING_ENFORCEMENT` | desligado | ninguém é barrado por saldo ou plano |
| `COMMERCIAL_GO_LIVE_AT` | não houve lançamento | nenhum consumo é cobrável |

Suspensão continua valendo sempre — é decisão humana, não consequência de saldo.

A fronteira é uma **data lida na hora**, não uma marcação gravada nas linhas: a
§22.3 proíbe `update token_usage_logs set billed = ...` como atalho. Desfazer é
mudar uma variável, não reescrever histórico.

---

## D22 — PENDENTE: o catálogo comercial

**27/07/2026** · SPEC-062 §45 · **bloqueia o Bloco B**

O que está construído e **não** depende de preço: medição (`usage_events` ligado
ao gargalo de LLM), custo por corretora/modelo/skill (§26), e as duas travas
acima.

O que **não** pode ser construído sem decisão do Founder:

1. **Preço dos planos** e o que cada um inclui, em RESULTADO e não em token
   ("300 cotações", não "2 milhões de tokens").
2. **A margem** sobre custo de provedor. Hoje o `sell_multiplier` no banco é
   `2.68` — herdado, não decidido.
3. **Provedor de pagamento.** Análise do Executor em 27/07: Stripe ou
   Asaas/Vindi/Iugu (~2-4%) contra Hotmart/Kiwify (~9-10%). Em R$ 2.000/mês a
   diferença é ~R$ 1.400 por cliente por ano.
4. **A data do `COMMERCIAL_GO_LIVE_AT`.**
5. **Teto de overage** e se existe trial.

**Recomendação registrada:** decidir depois de 30 dias medindo com a cobrança
desligada. O consumo real das corretoras é que dá o preço — hoje ele seria
palpite. Ver relatório de 27/07/2026.

---

## D23 — O Observador não desliga; o agente de atendimento só fala pelo botão

**27/07/2026** · SPEC-038/040/045 · auditoria de pareamento

### As regras, ditadas pelo Founder

1. **O Observador nunca desliga.** Pareou, observa — com o agente ligado ou
   desligado, hoje e daqui a um ano. Ele completa as rotas que faltam e
   atualiza quando encontra diferença.
2. **O agente de atendimento nasce desligado** e só é ligado pelo botão do
   dashboard.
3. Ligado, responde. Desligado, **nunca** responde: quem atende é a pessoa,
   direto no WhatsApp.
4. Cada corretora é independente: ligar o agente da Resulta não faz nada na
   AutoFleet.
5. Com o agente desligado, o **Cartógrafo fica parado** — o número pertence à
   atendente humana.

> Founder: "O AGENTE DE ATENDIMENTO NASCE DESLIGADO. ELE SÓ É LIGADO SE CLICAR
> NO BOTÃO DEPOIS DE PAREADO." · "O OBSERVADOR NUNCA DESLIGA. ELE É DIFERENTE
> DO AGENTE DE ATENDIMENTO."

### O defeito que a auditoria encontrou

`observer_tap` devolvia "consumido" sempre que a integração fosse
`purpose='observer'`, e o webhook faz `if _observed is not None: return`. O
dashboard pareia justamente com `purpose='observer'`.

**Toda mensagem morria ali — inclusive depois do clique em "Ligar agente".** No
dia 8 o botão viraria verde, a tela diria "Atendendo os segurados", e o agente
ficaria mudo para sempre. O pior tipo de defeito: tudo parece certo.

Causa: duas decisões diferentes coladas numa variável só. **Capturar** nunca
para; **consumir** para quando o agente assume.

### O que mudou

| Antes | Agora |
|---|---|
| consumia sempre que `purpose='observer'` | consome só enquanto o agente está calado |
| pareamento desligava o agente | pareamento não toca no agente |
| silêncio dependia do pareamento | silêncio vem do nascimento (blueprint + gatilho no banco) |
| Cartógrafo podia explorar durante a observação | Cartógrafo recusa com o agente desligado |

**Por que o pareamento parou de desligar:** re-parear é comum (telefone
desligado, logout, QR vencido, troca de aparelho) e **desligava um agente que
estava trabalhando**, sem avisar ninguém.

**Por que o Cartógrafo para:** ele explora mandando mensagem para a seguradora
pelo **mesmo número** da atendente. Com o agente desligado, é ela quem está
conversando com aquela seguradora naquele instante. O freio que existia
(`dispatch:active`) não cobria conversa de humano — o sistema não sabia que ela
estava lá.

### Garantias

ORQ-01 e OBS-02 no gate (44/44). Gatilho `atendimento_nasce_desligado` aplicado
e provado em produção: agente de atendimento criado com `is_active=true` nasce
`false`; o core continua nascendo `true`.

---

## P2 — A organização do primeiro nível do Admin  `RESOLVIDA — 02/08/2026`

> **Decisão delegada ao líder técnico pelo Founder** em 02/08, com o pedido de
> "pensar em como seria no GPT e no Claude para ser administrado".
>
> **FICAM OS OITO HUBS da SPEC-061.** A SPEC-064 I.3 é marcada como
> **SUPERADA** neste ponto.
>
> **Três razões:**
> 1. Os seis hubs da SPEC-064 **não cobrem tudo** — Financeiro, Conhecimento e
>    Governança sumiriam. Não é simplificação: é omissão.
> 2. O padrão do Claude e do GPT **não é "menos seções"** — é cada seção
>    responder uma pergunta inteira. Oito nomeadas por assunto já é isso.
> 3. O problema medido nunca foi a quantidade: eram **quatro telas no hub
>    errado**. Rótulo resolve o que hub novo só mascararia.
>
> **O que foi feito:** as quatro telas do catálogo se anunciam com prefixo —
> `Catálogo: Auxiliares`, `Catálogo: Agentes`, `Catálogo: Modelos de rotina`,
> `Catálogo: Skills, ferramentas e conectores`. Primeiro nível intacto em 8.

### Registro original do conflito


**Data de abertura:** 02/08/2026 · **Origem:** SPEC-064 Bloco I

### O conflito

Duas SPECs canônicas propõem estruturas diferentes para o primeiro nível do
portal admin, e **as duas foram escritas com razão.**

```
SPEC-061 §10   OITO hubs, aprovados por você depois de dizer
               "é uma bagunça e não consigo entender de fato tudo"
               (o Admin tinha chegado a QUINZE grupos)

               Visão geral · Corretoras · Operação · Inteligência ·
               Conexões · Conhecimento · Financeiro · Governança

SPEC-064 I.3   SEIS hubs, reorganizados pela ontologia

               Corretoras · Agentes · Auxiliares · Capacidades ·
               Operação · Inteligência
```

### Por que não decidi sozinho

A SPEC-061 §10 é explícita: *"não adicionar novo item de primeiro nível sem
revisão canônica"* — e há um teste automatizado que a faz valer.

**Eu cheguei a criar um nono hub e o teste me pegou.** Ele estava certo: seria
repetir, no admin, exatamente o que a SPEC-064 acabara de desfazer no menu do
corretor. **"O menu não cresce" vale para os dois lados.**

E trocar oito hubs que você aprovou por seis, de passagem, no fim de uma
execução, sem você ver — isso não é revisão canônica. É decisão de arquitetura
tomada sozinho, que o CLAUDE.md §10 proíbe.

### O que foi feito enquanto isso

📊 O problema que a auditoria mediu era real: o submenu "Inteligência" tinha
**nove itens, e quatro respondiam outra pergunta** — *"o que o sistema sabe
fazer"* em vez de *"o que o sistema percebeu"*.

**A separação foi feita dentro do submenu**, que a §10 deixa livre: as quatro
telas do catálogo passaram a se anunciar com o prefixo `Catálogo:`. O primeiro
nível continua com oito.

```
O que o sistema percebeu      ← "o que ele viu"
O que buscamos na internet
O que as corretoras pediram
Garimpo (legado)
Catálogo: Auxiliares          ← "o que ele sabe fazer"
Catálogo: Agentes
Catálogo: Modelos de rotina
Catálogo: Skills, ferramentas e conectores
Blueprint Center
```

**Resolve a confusão sem crescer o menu.** É a solução mínima honesta enquanto
a decisão maior não é sua.

### O que preciso de você

**Ficamos com os oito hubs da SPEC-061, ou passamos para os seis da SPEC-064?**

Se ficarmos com oito, a SPEC-064 I.3 é marcada como **superada** e a solução
acima vira definitiva. Se passarmos para seis, é uma mudança visual grande no
admin e merece uma leva própria — não o rabo de uma SPEC.

---

## D-Canal-01 · Um pareamento, duas funções, uma boca — 03/08/2026

**Decisão do Founder, palavras dele:**

> *"Conectou uma vez, está ligado para atendimento e para observador. O
> observador nunca fala nada, nunca responde, só o atendimento. O atendimento
> nasce desligado e precisa clicar em Agente de Atendimento para ele começar a
> responder, senão mesmo conectado continua mudo. O observador é sempre em
> silêncio."*

**Isto encerra a P-68.** O conflito era entre a SPEC-069 (*"observer nunca é
canal de saída"*) e o código, que responde o segurado pela integração que
recebeu — inclusive quando ela se chama `observer`.

**A decisão resolve dizendo que os dois estavam certos sobre coisas diferentes:**

```
OBSERVAR   é uma FUNÇÃO, e ela é muda por natureza. Nunca inicia, nunca
           responde, não tem voz. Roda sempre, do pareamento em diante.

ATENDER    é a outra FUNÇÃO no MESMO número. É ela que fala. Nasce
           DESLIGADA e só passa a responder quando alguém liga o agente.
```

**Não são dois números e não são dois pareamentos.** O que existia era um `purpose`
chamado `observer` fazendo as duas coisas — e a SPEC lendo esse nome como se
fosse a função.

**O que muda no texto:** SPEC-069 passa a dizer *"a função de observação nunca
emite; quem emite é o atendimento, e ele nasce desligado"*. 📊 O código já se
comporta assim: `pairing_orchestrator.py` faz o agente nascer desligado e
`attendance_agent_active` é fail-closed (falha de leitura = silêncio).

**O que fica pendente:** o `purpose` continua se chamando `observer` enquanto
carrega as duas funções. Renomear é seguro só com migração — fica em [P-65].

---

## D-Vidros-01 · O Atendente opera o portal de vidros ponta a ponta — 04/08/2026

**Decisão do Founder, palavras dele:**

> *"Se a pergunta foi se o agente de atendimento pode operar o portal de vidros?
> A resposta é sim, óbvio. Ele deve operar de ponta a ponta. É importantíssimo
> que seja um atendimento que a gente nunca erre, porque tem volume."*

E, sobre a trava:

> *"Portal funcionando sem erros e sem o agente travar, e nós conseguirmos o mais
> perto de 100% de atendimentos com sucesso possível, é um dos principais
> objetivos nossos. Ideal é 100% de sucesso, mas sei que alguma trava pode
> acontecer e precisamos de handoff pra isso também. Não pode ficar travado."*

**Isto encerra a P-70.**

### E a pergunta estava mal formulada — por minha conta

Eu registrei isso como *conflito canônico entre a SPEC-053 e a SPEC-020*. 📊 Medido
em 04/08/2026, **não havia conflito.** A SPEC-053 §5.2 diz, literalmente:

> *"corredores definidos; menor privilégio; (…) sem ferramentas genéricas de
> gestão, marketing ou administração"*

Ela proíbe **ferramenta genérica**, e manda usar **corredor definido**. São coisas
diferentes, e o registro já sabia disso:

```
tenant.portal.execute                  entre em qualquer portal, faça qualquer
                                       coisa.  GENÉRICA.  attendance: NEGADA ✅
                                       (e continua negada — está certo)

operational.portal.assistance.prepare  abra atendimento de vidros, sem enviar.
operational.portal.assistance.request  envie, com aprovação.
                                       CORREDOR.  attendance: LIBERADAS ✅
                                       (desde sempre, nunca foram usadas)
```

O `portal_action` não é genérico: jornada fixa, parâmetros montados no servidor a
partir da InfoCap, `confirm=False` cravado no código. **É o corredor.**

**O que estava errado era o portão:** `graph.py` exigia a chave *genérica* para
soltar uma ferramenta *específica*. Corrigido no código, sem tocar na SPEC-053 e
sem afrouxar nada.

### E havia mais duas travas, que decisão nenhuma resolveria

📊 Medidas no mesmo dia, e nenhuma delas dependia de gente:

| Trava | O que estava escrito | Por que era impossível |
|---|---|---|
| provider nulo | `tenant.portal.execute.provider = NULL` + exige conexão | o resolver busca o slug **pelo nome** do provider. Nulo → lista vazia → `needs_connection` **para sempre**. Não existia conexão que resolvesse, nem tela onde clicar. |
| credencial de site sem login | as 3 de assistência exigiam conexão | 📊 `portals.cred_kind = 'public'` nos **2** portais de vidros. Exigia cadastrar credencial de um site que não pede credencial. |

Consequência prática: a AutoFleet — e **toda corretora que entrar amanhã** — era
barrada para abrir vidros, num portal que qualquer pessoa abre no navegador.

### O que fica de pé

- `tenant.portal.execute` **continua negada** ao Atendente. A SPEC-053 §5.2 fica
  intacta, e um teste reprova quem tentar "resolver o conflito" religando-a.
- Cobrança e apólice acontecem em portal de corretor (📊 15 portais, todos
  `login_password`) e **continuam exigindo conexão**.
- O envio real segue com aprovação (`assistance.request`,
  `requires_approval: true`) e atrás do `PORTAL_REAL_ENABLED` no worker.

### O último interruptor é do Founder

📊 Os quatro agentes de atendimento do sistema estão com `is_active = false` —
Saionara (Resulta), Maria Regina (AutoFleet), JOANA (Amandus), Even (Blueprint).
Isso **não é defeito**: é o modo observação da [D23], funcionando como desenhado.
Enquanto estiver assim, o agente captura e não fala — inclusive não aciona portal.

**Ligar o agente de atendimento é o gesto que liga tudo isto.** É do Founder, e é
um clique.

---

## D-Observador-02 · Telefone pareado é telefone OFICIAL de atendimento — 04/08/2026

**Decisão do Founder, palavras dele:**

> *"São os números oficiais da corretora para atendimento. Sempre que for
> conectado um WhatsApp no atendimento e acionamento da corretora, esse celular
> deve ser tratado como telefone oficial de atendimento e deve baixar as
> conversas para ser feita a curadoria depois, destilação, criação de novas
> cartas."*

E o limite, na mesma frase:

> *"Mas é preciso ter cuidado com conversas pessoais, conversas que não têm valor
> para o cérebro e não devem virar carta. **Não precisamos ter milhões de cartas.
> Precisamos ter um cérebro inteligentíssimo que entende tudo de seguros.**"*

**Isto encerra a P-84.**

### A regra arquitetural que sai daqui

> **A captura é ampla. O juízo de valor é da DESTILAÇÃO.**

```
CAPTURAR   telefone pareado por corretora = oficial de atendimento
           -> observer_scope = insurers_and_clients, sempre

DESTILAR   "isto aumenta a inteligência do cérebro?"
           -> conversa pessoal, papo sem valor: NÃO vira carta
```

Isso resolve a tensão que me travava. Eu tinha tentado estreitar a captura para
proteger contra dado pessoal, e estava resolvendo o problema na camada errada:
capturar de menos perde material que não volta, e a proteção que importa é
**não publicar no RAG**, não **não gravar**.

📊 Aplicado no mesmo dia às três integrações de observador (AMANDUS, AutoFleet,
Resulta), que estavam em `insurers_only` — não por escolha, e sim porque foi
assim que a **contenção de 29/07** as deixou. Uma emergência tinha virado
política sem ninguém decidir.

**O que fica pendente:** o filtro de valor na destilação ainda não existe como
peça nomeada. Vai em [P-87] junto com religar o destilador.

---

## D-Portal-02 · As travas de teste saem; o interruptor é o "Ligar agente" — 04/08/2026

**Decisão do Founder, palavras dele:**

> *"A questão de trava no final sempre foi por um motivo exclusivo. Eu estava
> fazendo os testes no meu próprio celular e era apenas teste nos atendimentos.
> Se não tivesse a trava, seriam feitos os acionamentos dos serviços de vidro de
> verdade. Essa é a única função da trava que coloquei na época."*
>
> *"Se o atendimento estiver pronto no portal, podemos tirar as travas, **desde
> que os agentes de atendimento permaneçam desligados ainda**. Quero tudo pronto
> e funcionando, mas o agente de atendimento tem que continuar desligado. É pra
> ficar tudo pronto e desligado."*
>
> *"Se tiver alguma trava no atendimento de WhatsApp também, onde é feito o
> acionamento, também pode tirar a trava dos corredores."*
>
> *"No momento em que apertar o LIGAR AGENTE, aí os corredores que tiverem
> ativados funcionarão."*

**Isto encerra a P-90.**

### O que muda, e o que passa a segurar

Eram DUAS travas, e nenhuma delas era de segurança do produto — as duas eram
andaimes de teste:

| Trava | Por que existia | Estado |
|---|---|---|
| `confirm=False` cravado | os testes do Founder no celular dele abririam serviço de vidro de verdade | **sai** |
| dry-run do corredor de WhatsApp | mesma coisa, no acionamento por WhatsApp | **sai** |

**O que passa a segurar é UMA coisa só, e ela é visível numa tela:**

```
agents.is_active = false   ->  o agente não atende, não aciona, não abre portal
                               (📊 os quatro estão false)

clique em "Ligar agente"   ->  tudo funciona ponta a ponta
```

É melhor assim do que com as travas: uma trava escondida no código faz alguém
apertar o botão verde e não entender por que nada acontece. Um interruptor só,
com nome, é auditável.

### O que continua travado, e não sai

- **O modo observação é mudo** — nenhum caminho fala com o segurado com o agente
  desligado. É a regra da [D23], e ela tem guarda próprio.
- **Idempotência do portal** — 📊 o protocolo nasce no passo 7 ANTES do fim do
  fluxo; reexecutar cria um SEGUNDO atendimento, e o índice único impede.
- **Sinistro nunca vira portal** — colisão, roubo e incêndio continuam handoff.

---

## D-Gate-01 · A SPEC-063 fecha o portão de CÓDIGO; a prova viva vai para a 068 — 04/08/2026

**Decisão do Founder:** autorizou a recomendação do líder técnico, literal:
*"pode fazer"*.

### O diagnóstico que levou a isso

📊 A SPEC-063 tem **dois portões, e só um pode ser fechado por código.**

```
portão de CÓDIGO      165 testes verdes · tudo em produção        ✅ FECHADO
portão de PROVA VIVA  um WhatsApp pareado atendendo um segurado   ← nenhuma
                      de verdade, sem incidente                      linha de
                                                                     código
                                                                     produz isto
```

📊 **32 pendências nasceram dela. 24 seguem abertas — 11 dependem do Founder,
13 de execução.** E a causa não é falta de trabalho:

> **A SPEC cresceu para além do próprio texto.** Previa 8 blocos; a execução
> entregou 11 + uma Fase 0 com 11 consertos estruturais + descobriu 5 fases
> seguintes. Cada auditoria achou defeito real — o CPF vazava por dois caminhos,
> o freio não disparava em 28 de 33 vezes, o portal parava no 80% para sempre.
>
> É trabalho legítimo. Mas **sem critério de parada, uma SPEC de atendimento não
> termina nunca**, porque sempre há mais um nó de URA para mapear.

### O que muda

- A **SPEC-063 está encerrada** no que diz respeito a código.
- A **prova viva** (§6.1 dela) passa a ser item da **SPEC-068**, que é
  exatamente o portão de go-live e existe para isso.
- As 13 pendências 🤖 dela continuam válidas e nomeadas, mas **não bloqueiam o
  encerramento** — elas viram fila da 068 ou de quem as herdar.

### Os três atos físicos, numa sessão só

1. Um grupo de WhatsApp **por corretora** (hoje AutoFleet e Resulta apontam para
   o mesmo, e o roteador recusa de propósito — P-85)
2. Parear os números
3. **Ligar o agente na AMANDUS primeiro** — 📊 a `ATTENDANT_INBOUND_ALLOWLIST`
   já limita a um número, então é teste seguro por construção

### Por que isto não é abrir mão de qualidade

Nada foi afrouxado: os 165 testes continuam verdes, os guardas continuam de pé,
e as pendências continuam escritas com dono. O que muda é **onde a régua de
"terminou" fica** — e ela sai de um lugar onde nenhum código a alcança.

---

## D-Identidade-01 · Desconversar é legítimo; negar que é IA, nunca — 05/08/2026

**Decisão do Founder, na íntegra:**

> "NAO É PARA DIZER HUMANO E NEM PARECER NUNCA SER UMA IA. SE PERGUNTADO, PODE
> DAR UMA RESPOSTA DESVIANDO... E AI SE PERGUNTAR DE NOVO FALAR QUE É UM AGENTE.
> NAO MENTIR QUE NAO É."

### As três fases, e o que muda entre elas

| Fase | Situação | Conduta |
|---|---|---|
| **1** | ninguém perguntou | não anuncia nada — atende |
| **2** | perguntou uma vez | desvia **para o trabalho**, sem negar |
| **3** | insistiu | **assume**: "sou um agente digital da corretora" |

💭 Exemplo da fase 2: *"Sou do atendimento aqui da corretora 🙂 Já estou com o
seu caso na mão — me confirma o endereço?"*

💭 Exemplo da fase 3: *"Sou sim — sou um agente digital da corretora, e tem
gente da equipe acompanhando. Seguindo: seu guincho já está solicitado, previsão
de 40 minutos."*

### As frases proibidas em qualquer fase

```
"sou uma pessoa"   ·   "sou humano"   ·   "juro que não sou robô"
```

**Não é preferência de tom: é a linha entre discrição e mentira.** Desviar
uma vez é o que qualquer atendente faz quando a pergunta não ajuda o cliente.
Negar é afirmar um fato falso a alguém que perguntou explicitamente — e o
segurado tem direito à resposta quando insiste.

### O que fecha a porta dos dois lados

Depois de assumir na fase 3, **não se volta a desviar**. Reaparecer com
evasiva depois de ter assumido é pior que qualquer uma das duas posturas
isoladas: lê-se como recuo, e destrói a confiança que a resposta honesta
tinha acabado de construir.

### Onde isto vive

`backend/app/core/prompts.py`, bloco 🪪 QUEM ESTÁ FALANDO, dentro de
`ATTENDANCE_BASE_PROMPT`. Guardado por
`backend/tests/test_o_atendimento_soa_humano.py`.

Vale para **quem fala com o segurado**. Do outro lado — a conversa com a
seguradora — a regra é outra e já está decidida: o corredor se identifica como
a corretora, porque é a corretora que aciona.

---

## D-Playbook-01 · PENDENTE: o eixo do playbook de conduta — 07/08/2026

### A pergunta do Founder

> *"Será que isso não é uma simplificação barata num sistema tão robusto e
> detalhado? Será que ao invés de OUTRO, não é melhor termos playbooks com
> nomes de ramos de verdade como condomínio, empresarial, vida?"*

A intuição está certa e o eixo era outro. Medindo, o `outro` que custa caro
não é o do ramo — é o do **serviço**.

### O que foi medido — 07/08/2026, 9.196 sessões destiladas

**O ramo `outro` não é um balde vazio nem um problema:** 2.905 sessões (32%),
segundo maior. `outro/sinistro` (629 úteis, nota 74,5) e `outro/consulta` (254,
nota 69,6) são playbooks reais e grandes.

**O serviço `outro` é descartado por código**, e leva junto o melhor material:

```
auto/outro            2.219 úteis   nota 74,4   SEM PLAYBOOK  ← maior E melhor
outro/outro           1.468         nota 67,2   SEM PLAYBOOK
residencial/outro       166         nota 76,3   SEM PLAYBOOK
vida/outro               24         nota 72,9   SEM PLAYBOOK
```

**E a informação para separá-los já está gravada.** O classificador escreve
`tipo` e `servico`; o playbook lê só `(ramo, servico)`. Dentro de
`servico='outro'`, o `tipo` diz:

```
auto/cobranca         1.904 úteis   nota 76,2   ← melhor grupo do acervo inteiro
outro/cobranca          986         nota 72,7
outro/outro             381         nota 52,4   ← o único que é ruído de verdade
residencial/assist.     109         nota 78,5
```

**Os ramos que o Founder citou, contra as 12.063 cartas do RAG:**

| tema | cartas | % |
|---|---|---|
| **cobrança** | **2.915** | **24%** |
| condomínio | 468 | 3,9% |
| empresarial | 80 | 0,7% |
| frota | 74 | 0,6% |
| responsabilidade civil | 41 | 0,3% |
| fiança | 25 | 0,2% |
| saúde | 6 | 0,05% |

Condomínio é o único dos ramos novos com massa real. Os outros não estão no
material porque as duas corretoras capturadas são de auto e residencial —
**ausência de material não é prova de que o ramo não importa**, é prova de que
estas duas corretoras não o trabalham.

### Por que ramo e assunto não são o mesmo eixo

O par `(ramo, serviço)` foi desenhado para **assistência**, onde funciona
perfeitamente: guincho é auto, encanador é residencial, e o ramo determina o
prestador, a cobertura e a pergunta.

Mas há trabalho de corretora em que o ramo **não muda a conduta**. Uma conduta
medida de cobrança, do acervo real:

> *"Explicou por que não conseguia gerar o boleto: a forma de pagamento
> contratada é débito em conta."*

Isso vale igual em auto, residencial ou vida. O que muda é o sistema da
seguradora — não o ramo. E quando a conversa é sobre boleto, o segurado nem
menciona o ramo: diz *"não recebi o boleto"*. O classificador, sem sinal de
ramo, escolhe `outro` — e o rótulo passa a dizer "não sei o que é isso" sobre
uma conversa que o sistema classificou muito bem: é cobrança.

### As três saídas

**A. `outro` vira ausência, não valor** — quando `servico == "outro"`, usar
`tipo` como chave. Uma linha de escolha de chave. Não inventa ramo, não mexe no
classificador, não migra dado. Faz nascer `auto/cobranca` (1.904 úteis, nota
76,2) já acima do piso. **Recomendada.**

**B. Acrescentar os ramos citados** (condomínio, empresarial, RC, fiança,
saúde) à lista do classificador. Resolve 620 cartas (5%) e **não toca nas 2.915
de cobrança**. Cria cinco ramos abaixo do piso de 12 — playbooks que não
nascem. Não é errada: é ortogonal ao problema, e fica melhor depois de A, com
material que a justifique.

**C. Não fazer nada.** O agente segue atendendo 24% do trabalho sem conduta
destilada, com 2.890 atendimentos humanos bons sobre o assunto gravados e não
lidos.

### 🔴 Decisão pendente do Founder

Registrado em [`PENDENCIAS.md`](PENDENCIAS.md) como **P-123**.
