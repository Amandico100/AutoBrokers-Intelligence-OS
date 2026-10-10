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

## D-Playbook-01 · O eixo do playbook de conduta — `DECIDIDA E EXECUTADA — 07/08/2026`

> **Decisão do Founder:** executar a saída **A** antes da destilação.
> **Executada** em `0d6e782`. E a investigação encontrou um defeito maior no
> caminho — o do runtime, na seção final desta entrada.


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

### 🔴 O defeito maior, achado ao verificar se a saída A funcionaria

Antes de executar, fui conferir se `auto/cobranca` seria **encontrado** pelo
agente. Não seria — e o motivo vale mais que a decisão de eixo.

**Existem dois classificadores, e eles não falam a mesma língua:**

| | quem **escreve** o playbook | quem **procura** em runtime |
|---|---|---|
| onde | `_STAGE1_SYSTEM` (LLM) | `infer_ramo_servico` (regex) |
| ramos | auto · residencial · **vida · outro** | auto · residencial |
| serviços | guincho… + **consulta** · sinistro | guincho… + sinistro |

📊 **6 dos 12 playbooks ATIVOS eram inalcançáveis:** `auto/consulta` (253
atendimentos), `outro/sinistro` (629), `outro/consulta` (254),
`residencial/consulta` (48), `vida/sinistro` (122), `vida/consulta`.

Escritos, versionados, exibidos no admin, pagos no modelo caro — e nunca lidos.
**A falha é silenciosa por construção:** a busca não acha linha e devolve
vazio. Um playbook que não existe e um playbook que não é encontrado produzem
exatamente o mesmo resultado.

É a terceira vez no mesmo dia que o padrão aparece — **duas descrições da mesma
coisa, divergindo em silêncio** (o Lapidador foi a primeira, o eixo a segunda).

### O que foi executado

1. **`chave_do_grupo()`** — uma regra de chave só, usada por quem conta, quem
   enfileira e quem sintetiza. Eram três contas: a de trás contava o grupo que
   a da frente descartava.
2. **`infer_ramo_servico`** ganhou `cobranca`, `apolice`, `renovacao` e o ramo
   `vida` — que ela transformava em `auto` pelo `else` do ternário, sem log.
   Vêm **depois** da assistência: quem liga sobre o guincho que não chegou está
   falando de guincho, mesmo citando o boleto.
3. **`graph._conduta_do_caso`** — sem playbook do ramo, procura o do ramo
   `outro`. Eles não são lixo: são a conduta daquele serviço quando o ramo não
   muda o que se faz. **Segunda** tentativa, nunca primeira.

O material antigo continua legível sem reescrever uma linha do banco:
📊 `auto/cobranca` acha 0 pela consulta nova e 1.904 pela do formato antigo.

📊 5 mutações, 5 reprovaram — inclusive a sutil, de o fallback virar primeira
tentativa e `outro/sinistro` ganhar de `auto/sinistro` numa conversa de carro.
Guarda: [`test_o_playbook_nasce_com_a_chave_que_o_agente_procura.py`](../../backend/tests/test_o_playbook_nasce_com_a_chave_que_o_agente_procura.py).

### O que a saída B (ramos novos) continua valendo

Não foi executada e **não está descartada**: é ortogonal, e fica melhor depois
que houver material que a justifique. 📊 Condomínio é o único dos citados com
massa real (468 cartas). Registrado em `PENDENCIAS.md`.


---

## D-Acervo-01 · O conhecimento destilado não tem dono — 08/08/2026

### A pergunta

📊 `knowledge_cards` não tem coluna `company_id`. As 12.933 cartas nascem de
conversas reais da Resulta e da AutoFleet e viram conhecimento **global**, lido
por todas as corretoras. A única proteção é uma variável de ambiente de
exclusão: a corretora entra por padrão e sai se alguém lembrar de editar.

Um auditor levantou isso como candidato a P1 de multi-tenant.

### A decisão do Founder, nas palavras dele

> *"Não interessa se a conversa veio da Resulta ou da AutoFleet. O que importa
> é o conhecimento global de seguros. (…) Cartas criadas nas memórias e
> conhecimento vindo da SUSEP ou das seguradoras **não têm dono depois de
> destilados**. Isso se transforma em conhecimento do AutoBrokers a serviço de
> todas as corretoras que perguntarem."*

E a razão de produto:

> *"Quanto mais inteligente for o cérebro, mais valiosos ficamos no ramo dos
> seguros e mais as corretoras vão querer usar."*

### O que isto decide

**O acervo destilado é global por desenho, não por omissão.** Não haverá
`company_id` em `knowledge_cards`, não haverá filtro por corretora na busca de
conhecimento, e a variável de exclusão deixa de ser salvaguarda de privacidade
— ela serve só para manter corretora de **teste** fora do acervo.

### 🔴 A linha que esta decisão NÃO move

**Conhecimento é global; fato sobre pessoa nunca.** Nome, telefone, CPF,
placa, endereço, número de apólice, valor em reais de um cliente — nada disso
vira carta, e a decisão acima não abre exceção alguma.

📊 A proteção existe em três camadas e funciona: 310 cartas foram rejeitadas
por `rejected_pii`, e o `templatize` é reaplicado no momento da publicação (a
terceira camada) — 📊 5 cartas publicadas antes falharam nessa reconferência em
08/08/2026, o que prova que a régua ainda morde.

E a segunda linha, criada em 08/08/2026: **conversa que não é sobre seguro não
vira carta** (`e_sobre_seguro`, status `rejected_fora_de_escopo`). 📊 Calibrada
contra as 12.063 publicadas: recusaria 64 (0,53%).

> A diferença é simples: *"a Porto exige boletim de ocorrência para roubo"* é
> conhecimento e pertence a todas. *"O João da placa ABC1D23 abriu sinistro
> ontem"* é fato de uma pessoa e não pertence a ninguém além dela.

---

## D-Acervo-02 · Documento revogado sai da busca e vai para o arquivo morto — 08/08/2026

### A decisão

Quando uma condição geral nova entra, a anterior:

```
SAI     do índice de busca — não pode aparecer em "o que vale hoje"
FICA    guardada no arquivo (banco + MinIO), endereçável por (produto, data)
```

### Por que não apagar de vez

**Uma apólice vendida em 2024 é regida pelo contrato de 2024.** Quando esse
segurado reclamar de uma recusa, é essa versão que vale — e é justamente ele
quem reclama. Apagar seria perder a resposta para o caso que mais importa.

### Por que não deixar na busca

📊 A Porto Auto tem **100 versões** registradas na SUSEP; a Allianz Auto, 72.
Cem versões da mesma cláusula são cem quase-duplicatas: numa pergunta sobre
alagamento, as vagas que chegam ao agente se enchem com a mesma frase em anos
diferentes, e ele escolhe uma sem critério de data.

> O recurso escasso não é disco nem dinheiro — 📊 indexar tudo custaria US$
> 0,29. É o número de trechos que chegam ao modelo. Manter o revogado na busca
> não deixa o acervo mais caro: deixa **mais burro**, e em silêncio.

### Como se sabe qual está vigente

📊 O registro da SUSEP publica: **a versão vigente é a que tem Data de Fim de
Comercialização vazia**, sob produto com situação "Passível de comercialização".
Zero inferência.

### O que isto evita

📊 Hoje, 12 de 13 documentos indexados são versões revogadas — o condomínio da
Porto é de dezembro de 2012 e o vigente é de dezembro de 2025. **Treze anos.**
Um contrato revogado respondendo com a autoridade de documento oficial é pior
que documento nenhum: o segurado age sobre a resposta.


---

# 🔴 D-093 · O `finalize` abre de verdade, e o cancelamento é por pessoa, depois

> **25/08/2026** · registrada pela execução da SPEC-093, BLOCO E.
> ⛔ **Nenhuma variável de ambiente foi tocada.** Isto é registro.

## O que o Founder decidiu

> *"Nós vamos deixar o atendimento ser pedido e, se for fictício, elas vão
> cancelar depois de feito."*

📊 Isso é a **opção (A)** do BLOCO E: `DISPATCH_FINALIZE_MODE=live`, com o
cancelamento feito **por pessoa, depois do fato**.

## 🔴 A pergunta que a SPEC mandou MEDIR antes de aceitar

A SPEC-093 §BLOCO E escreve, com todas as letras:

> *"quanto tempo elas têm para cancelar antes de virar serviço de verdade?
> 🔴 não medido: ninguém sabe quanto a seguradora demora entre aceitar e
> despachar. Pode ser minutos."*
>
> *"A nº 2 é a que preocupa. 'Cancelar depois' só funciona se existir um
> 'depois'."*

**Medido em 25/08/2026, no acervo de conversas reais** (`observed_events`,
sessões em que a seguradora confirmou e alguém depois falou em cancelar):

```
sessões com confirmação da seguradora ........... 128
sessões em que a palavra "cancelar" aparece ......  86
as duas coisas na mesma sessão ...................  56
🔴 cancelamentos DEPOIS da confirmação ...........  12

   mais rápido .....    0,0 min
   mediana .........   34,3 min
   mais lento ......  103,5 min
   abaixo de 5 min .    5 de 12   ← 42%

   seguradoras: allianz · porto · tokio
```

## ✅ O que isso responde

**"Cancelar depois" EXISTE e é praticado.** 📊 Doze vezes no acervo, mediana de
**34 minutos**. A premissa da decisão do Founder se sustenta: há um *depois*.

## 🔴 O que isso NÃO responde — e é o que preocupa

⚠️ **Eu medi quando um HUMANO cancelou. Não medi quando ficou TARDE DEMAIS.**

São perguntas diferentes, e a segunda é a que custa dinheiro:

```
o que eu medi ......... quanto tempo depois da confirmação alguém cancelou
o que a SPEC pergunta . quanto tempo a seguradora leva entre aceitar e DESPACHAR
```

📊 **E 5 dos 12 cancelamentos aconteceram em menos de 5 minutos.** 💭 Duas
leituras cabem, e o acervo não separa: ou a pessoa percebeu o erro na hora, ou
**ela sabia que tinha pouco tempo**. A segunda leitura é a que importa, e ela
não é distinguível daqui.

⚠️ **E o método é por palavra-chave** (`ILIKE '%cancel%'`), não por desfecho
registrado. 📊 `work_runs` tem **4 acionamentos na história inteira** e
**nenhum** chegou a `captured` — não existe a série durável que responderia
isso direito.

## 🔴 A recomendação da execução, e ela é conservadora

> **A opção (A) está registrada como a decisão do Founder. O que a execução
> acrescenta é o SEGUNDO parâmetro, que a SPEC deixou em aberto:**

```
1  abre em TODOS os corredores, ou só nos completos?
   → 🧑 DECISÃO DO FOUNDER, não tomada. `DISPATCH_FINALIZE_LIVE_PLAYBOOKS`
     gradua corredor a corredor, e o padrão dele hoje é o conservador.

2  quanto tempo para cancelar?
   → 📊 mediana de 34 min no acervo · 42% abaixo de 5 min
     ⚠️ mas isso mede o CANCELAMENTO, não o PRAZO. O prazo continua não medido.
```

⛔ **A execução não tocou em variável nenhuma**, e o BLOCO F confere isso.


---

# 🔴 F-094-07 · 03/09/2026 · A conexão InfoCap da AMANDUS é a conta da RESULTA — P1 cross-tenant, decisão do Founder

**O que foi medido (censo da SPEC-094, `docs/canon/providers/infocap/INFOCAP-CORPAPI-CENSUS-v2.md`):**
📊 as conexões `connected` de Amandus e Resulta em `tenant_connections` descriptografam para a **mesma conta CorpAPI**
(mesmo `user_sha`, mesmo `pass_sha`, mesmo perfil `codigo 75`) e devolvem a **mesma carteira ao centavo** —
1.680 apólices tipo A em 2025, R$ 1.863.830,79 de `val_c`. Os ciphertexts são diferentes (IV aleatório do Fernet), então
a tabela não denuncia; só a descriptografia.

**Por que é P1 (CLAUDE.md §7 e §10 (4)):** qualquer leitura feita "pela Amandus" pelo caminho da conexão mostraria a
carteira da Resulta com o nome da Amandus — em tela, Artifact, briefing ou chat. Hoje ninguém lê por esse caminho
(a 081 resolve por nome e não há `CORP_INFOCAP_AMANDUS_*` em lugar nenhum), por isso o defeito está adormecido.
A SPEC-094 liga o caminho da conexão — e por isso parou aqui.

**A pergunta, em uma linha:**
```
Amandus e Resulta são a MESMA corretora legal/operacional na InfoCap?
  (A) SIM  → a SPEC trata as duas como UM tenant de dados; o gate de conta compartilhada aceita o par declarado
  (B) NÃO  → a conexão da Amandus está ERRADA: arquivar e cadastrar a conta certa (ação física sua)
```

**O que a execução faz até a decisão:** o adapter da 094 grava `account_fingerprint` na provenance e **recusa** a segunda
corretora que resolva para uma conta já usada por outra ("conexão compartilhada — F-094-07"); o canário da Amandus
**não roda**; nenhum Artifact é publicado para ela. Pendência P-094-CONTA-COMPARTILHADA (🧑).


---

# F-094-08 · 03/09/2026 · O fornecedor da API é a mesma casa dos dois maiores concorrentes de gestão

📊 `curl -sSI https://www.infocap.com.br/` → **301 → https://www.agger.com.br**; a Agger publica o produto **ONE**, "nascida da união entre
Quiver e Agger" (pesquisa `docs/canon/pesquisa/RELATORIOS-QUE-VALEM-DINHEIRO.md`). A CorpAPI de que o AutoBrokers depende pertence ao
grupo que vende Quiver. 📊 Nenhum dos 7 sistemas de gestão do mercado (Quiver, Segfy, Agger, TEx, Moshe, SGCOR, BIBlue) publica
developer portal — a camada de API deste mercado está na SEGURADORA (portais, Opin), não no sistema de gestão.
**O que isso muda:** a SPEC-094 já isola a InfoCap num adapter (a fórmula nunca conhece provider). A decisão estratégica — quanto
investir em Opin/portais das seguradoras como fonte primária em vez da CorpAPI — é sua. **Dono:** 🧑.

# F-094-09 · 03/09/2026 · Um agente pode ESCREVER no InfoCap — por cinco portas, nenhuma medida

📊 Coleção Postman oficial (export sem autenticação, 51 requests, 22 de escrita): `POST/PUT/DELETE /endereco /email /telefone` ·
`POST /cliente` (sem PUT: não existe "corrigir") · `POST /negocio` (funil, 38 chaves) · 🔴 `POST/PATCH/DELETE /prod_docs` (muda quanto a
corretora paga a quem) · 🔴 fluxo InCorp (PDF → `/incorp` → `/incorp_contexto` → `/incorp_documento` grava a apólice).
🔴 NÃO dá para abrir atendimento nem tarefa (só leitura). Riscos: sem idempotência (retry duplica cliente); 0 de 19 escritas tem resposta
documentada; e a conta compartilhada (F-094-07) faria uma escrita "da Amandus" cair na Resulta.
**A pergunta:** libera escrita para agentes, em que portas, com Approval (SPEC-055) obrigatório? Recomendação da execução: só a porta 1
(contato) e a 2 (cliente novo), atrás de Approval, DEPOIS de medir uma escrita real em ambiente de teste da InfoCap — nunca na Resulta
primeiro. **Dono:** 🧑.

# F-094-10 · 03/09/2026 · Prazo externo: 01/10/2026 a mensagem de serviço do WhatsApp deixa de ser grátis

📊 Tarifas Meta (conferidas por consistência de câmbio): Marketing R$ 0,3217 × Utility R$ 0,0350 por mensagem — template mal
categorizado custa 9,2×. 28 dias. Cabe a quem cuida da cobrança e do atendimento classificar os templates antes. **Dono:** 🧑/🤖.

---

# F-095-01 · 04/09/2026 · A leitura do modelo por cima do Pulso 360 — a primeira frase de modelo num relatório do produto

📊 A SPEC-095 deixou a narrativa dos relatórios **determinística por detector** (título com o número, por que importa, o que
fazer): nenhum número, título ou ação sai de um modelo. O que o Founder pediu em 04/09 ("como o ChatGPT e o Claude entregam")
inclui uma camada a mais: uma **leitura** em prosa por cima do pacote de evidência — o que os números, juntos, querem dizer.
**O que está pronto:** o pack selado (`pack_id`, `origem`), a régua que recusa número inventado (094: todo número do chat tem
ponteiro), e o bloco `prose` do renderizador. **O que falta é a sua autorização**, porque seria a primeira frase escrita por
modelo dentro de uma peça que a corretora guarda e reencaminha. Recomendação da execução: entrar marcada como "leitura do
AutoBrokers" (💭, nunca 📊), com um guarda que prova que **todo número da leitura existe no pack** e que a leitura some quando
o pack não tem achado. **Dono:** 🧑. 💭 3h quando autorizada.

# F-095-02 · 04/09/2026 · O briefing sai só no painel — WhatsApp e e-mail são decisão sua

📊 `delivery_detail` dos últimos briefings das três corretoras: `canais: [{canal: "dashboard"}]`, `push: true`. Nenhum WhatsApp,
nenhum e-mail, nenhuma mensagem sai (trava da leva). A repetição que o Founder sentiu era a LISTA (40 pares briefing×artifact,
35 peças de teste), não o envio. Mandar o briefing por WhatsApp/e-mail é: (a) o piso CRÍTICO da §3.2 (qualquer coisa que envia);
(b) o livro de entregas que saiu da proposta da 095 com gatilho ("o 1º envio real"); (c) o prazo de 01/10/2026 em que a
mensagem de serviço do WhatsApp deixa de ser grátis (F-094-10). **A pergunta:** quer o briefing fora do painel, para quem, e em
qual canal? **Dono:** 🧑.

# F-095-03 · 04/09/2026 · Decisões tomadas pela execução, registradas (protocolo §9: nota 0–100, escolha, siga)

- **A URL `/dashboard/entregas` fica; só o NOME vira "Relatórios"** — manter 85 × renomear 35 (4 redirects, links já entregues pelo
  chat, 2 guardas, `test_menu_nao_cresce.py` fixa key e href).
- **Os 35 relatórios de teste (34 Resulta + 1 AutoFleet) são ARQUIVADOS, não apagados** — reversível por UPDATE com o evento como
  registro; visíveis em "ver arquivados". Se algum for pergunta sua, diga: a lista sai antes de aplicar.
- **O placar conta só o que a corretora pediu e recebeu** (`source_type in ('chat','routine')`) — 📊 98,86% dos Work Runs são o
  relógio da plataforma; contá-los mentiria por 87×.
- **A narrativa é determinística, sem modelo** — 88 × leitura por modelo 70 (custo, latência, goldens e a regra "inferência marcada
  como leitura"). A leitura por modelo é a F-095-01.
- **O Fabric não muda** — promover a 1ª frase humana a manchete no briefing 80 × narrativa própria no `finding_engine` 60 × 3
  `signal_type` novos 55 (P-095-NARRATIVA-DO-FABRIC).
- **Identidade que casa peça ARQUIVADA cria peça nova**, não desarquiva — 85 × 45.

---

# F-096-00 · 04/09/2026 · As decisões que o Founder DELEGOU ao abrir a 096 — executadas com nota, antes do código da SPEC

O Founder, ao mandar executar a 096: *"as pendências você decide, com nota 0–100, e executa o que recomendou"*. Feito, nesta ordem:

- **F-094-07 → EXECUTADA como (B)**: "excluir o acesso do Amandus e deixar só da Resulta". A conexão InfoCap da Amandus
  (`604ec9f1…`, `status=connected`, 📊 nunca usada: `last_used_at` nulo) foi **arquivada** espelhando o escritor canônico
  (`app/api/vault/connections/[connectionId]/route.ts:161-164`: `status='archived'`, `metadata.archived={at,by,reason}`,
  `updated_at`) + a linha de auditoria que ele grava (`vault_audit_log`, `action='archive'`). 📊 VERIFY (SQL, 04/09 21:40 UTC):
  Amandus `archived · archived.by=orquestrador:F-094-07` · Resulta `a89ec28b… connected · healthy` · 1 linha de auditoria.
  ROLLBACK: `update tenant_connections set status='connected', metadata=metadata-'archived' where id='604ec9f1-…'`.
  Consequência: `_is_inactive_connection` (`infocap_connector.py:655-659`) já ignora `archived` — a Amandus deixa de resolver
  para a conta da Resulta; P-094-CONTA-COMPARTILHADA fecha. **Nota da opção: 90** (× manter 10: era P1 cross-tenant adormecido).
- **F-094.1-02 / F-094.1-08 → RECUSADA a proposta pendente**: `approval_requests` `e47a4a5c…` (Resulta, `metric.proposal`,
  `proposta.teste_builder_0941`, criada 04/09 05:55 pela execução da 094.1) foi **recusada pelo escritor existente**
  `WorkApprovalService.decidir(decisao='rejected')` (`approvals.py:194`), com o motivo gravado e `usuario_id` de um
  `admin_company` da Resulta. 📊 VERIFY: `status=rejected · decision=rejected · resolved_at 21:31 UTC`. Era métrica de TESTE,
  não de negócio — aprovar contaminaria o registry da corretora. **Nota: 85** (× aprovar 5 × deixar pendente 40: fila de
  aprovação com lixo de execução ensina a ignorar a fila).
- **F-094.1-01 (Tool Gateway) → FICA DESLIGADO**, sem ação nesta leva. 📊 155 diffs em sombra, 0 idênticos (relatório da 094.1):
  ligar sem paridade medida troca o comportamento de TODA tool do chat às cegas — e a 096 está prestes a instrumentar o stream
  de tools (`stream_agent_eventos`), o que é exatamente a régua que faltava para medir a sombra por tool. **Nota: desligar 85 ×
  ligar 15 × cutover parcial agora 35.** Volta na SPEC-109 (Engine) ou quando um relatório de sombra mostrar ≥ 95% de paridade.
- **F-094.1-03 (094.2 · comissão recebida/inadimplência via portal) → FICA NA FILA depois da 098** (o que o INDICE já dizia).
  📊 É o piso CRÍTICO (portal = credencial + envio), 💭 6–8h, e depende da 098 (cada coisa sabe de quem é) para não repetir a
  conta compartilhada. **Nota: depois da 098 75 × antes da 097 40 × nunca 20.**
- **F-095-01 (leitura do modelo no Pulso) → AUTORIZADA pelo Founder**; execução planejada como unidade LEVE separada
  (`P-095-LEITURA-DO-MODELO`): entra marcada "leitura do AutoBrokers" (💭), com o guarda "todo número da leitura existe no pack"
  e some quando o pack não tem achado. 💭 3h. Não entra na 096 (RISCO/SUPERFÍCIE diferentes; um escritor por arquivo).
- **F-095-02 (briefing por WhatsApp/e-mail) → PENDÊNCIA documentada** em `PENDENCIAS.md` (`P-095-BRIEFING-POR-CANAL`), com o
  que um chat futuro precisa saber para executar sem reabrir a pesquisa.


---

## D-E001-01…10 · A operação dos pilotos — as decisões que governam a SPEC-EXTRA-001 — 07/09/2026

**Decisões do Founder, tomadas na conversa de planejamento de 06–07/09/2026 e no prompt de abertura da EXTRA-001.** Registradas aqui pelo orquestrador ao converter a proposta; nenhuma delas é interpretação.

| ID | decisão | como entra no produto |
|---|---|---|
| **D-E001-01** | Prioridade imediata: fechar a cobrança e preservar o atendimento nos pilotos (Resulta, AutoFleet) | a EXTRA-001 passa na frente da 099 |
| **D-E001-02** | O atendimento continua no Evolution Go; não migrar provedor agora | nenhuma linha de `integrations` é criada, renomeada ou desativada |
| **D-E001-03** | Cobrança e atendimento usam, por ora, o MESMO número pareado da corretora; não exigir segundo QR | a cobrança sai pela conexão da corretora com `permite_envio_de_auxiliar=true` (regra da SPEC-078 B), fixada e revalidada no efeito |
| **D-E001-04** | Dois modos reais: *encaminhar para a equipe* e *enviar direto ao cliente* | `send_mode` ∈ {`equipe`, `cliente`} com motor; `test`/`none` continuam; `approval`/`live` antigos ficam retidos com explicação |
| **D-E001-05** | No modo equipe, texto e PDF vão prontos para encaminhar, sem marca de teste nem instrução interna misturada | nota interna em mensagem própria; o texto final é o mesmo que iria ao cliente |
| **D-E001-06** | Respostas do cliente, anti-repetição e aviso de falhas são parte do produto completo desta EXTRA | contexto do caso no atendimento; retorno registrado no ledger; reserva antes do efeito; incidentes em Atividades |
| **D-E001-07** | Testes vivos SOMENTE entre os dois números de teste do Founder (TESTE-A e TESTE-B, valores fora do repositório); os números operacionais da Resulta e da AutoFleet estão proibidos | allowlist privada no env do canário; guarda no último ponto de efeito; 📊 a conexão ativa da Resulta É TESTE-A (…4743), medido em 07/09 |
| **D-E001-08** | Criar a família EXTRA; manter 099→114 numeradas, com a execução linear pausada temporariamente | `SPEC-EXTRA-001…`; a polícia do protocolo passa a reconhecer a família |
| **D-E001-09** | Depois: investigação Agger (EXTRA-002), canais após os pilotos (099), renovação e demais auxiliares em propostas próprias | fila registrada no INDICE e no dossiê |
| **D-E001-10** | Atualizar o dossiê de SPECs ao longo do trabalho, não só no encerramento | página `#extra001` republicada a cada bloco fechado |

**Não decidido (fica na caixa do Founder da EXTRA-001):** ligar o agente de atendimento da Resulta por uma janela curta para provar a resposta automática ao vivo (a allowlist de entrada de produção contém só TESTE-B).

## Decisões dos pilotos — 08/09/2026 (véspera dos atendimentos reais)

| # | decisão | efeito |
|---|---|---|
| **D-PILOTO-01** | Conhecimento de atendimento e pós-acionamento (cartas, respostas, regras) é **GLOBAL**: toda corretora conectada usa o mesmo, nunca por corretora | `publicar_cartas_0971.py --global` publica no tenant Global Knowledge; retrieval tem de ler o global (ver relatório U5) |
| **D-PILOTO-02** | **Não** encerrar em lote as 467 conversas abertas da AutoFleet: o agente responde de qualquer forma e é melhor que responda com o histórico | nada a fazer; a Regina responder pelo celular pausa o robô naquela conversa, e isso é o desejado |
| **D-PILOTO-03** | Ligar o agente com HDI e Yelum mesmo com o formulário nativo; a trava de laço (P-092-10) entra hoje | U2 |
| **D-PILOTO-04** | Follow-up do pós-acionamento sai depois do horário combinado com o prestador (ou do protocolo) e **só entre 8h e 19h** no fuso da corretora; fora disso fica para a manhã seguinte | U5; `POS_ACIONAMENTO_ESPERA_MINUTOS=90` |
| **D-PILOTO-05** | Coleta dirigida (delegada ao orquestrador): percorrer a URA até a tela de confirmação e **recusar**; nunca confirmar chamado sem demanda real. O protocolo dessas rotas fica para o primeiro cliente de verdade | evita despachar prestador por engano; a rota ganha as telas, não o desfecho |
| **D-PILOTO-06** | Executar o essencial de 08/09 **sem o protocolo AAA** (14% do pacote semanal de tokens): builders Opus por unidade, orquestrador como juiz, testes por unidade | `PLANO-PILOTOS-AJUSTES-2026-09-08.md` |
| **D-PILOTO-07** | Meta explícita: ≥4 atendimentos simultâneos por corretora e nenhuma corretora interferindo em outra | P-PILOTO-01 |
| **D-PILOTO-08** (12/09) | Numeração **EXTRA-001.1…001.9** mantida; blocos novos continuam a sequência (001.0 retroativa, 001.10 portal de vidros); EXTRA-002…010 não renumeram | `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §7.1 |
| **D-PILOTO-09** (12/09) | Lista de números da casa (telefones da equipe e outros números que o agente nunca atende) no **card Equipe** | EXTRA-001.3 |
| **D-PILOTO-10** (12–13/09) | Humano da corretora na URA: **opção C** — pausa de **60 s** (📊 medido contra 56 encerramentos reais de URA: Porto 95 s, Allianz 103 s são os piores; 90 s viraria 110 s pelo ciclo de 20 s do Vigia), renovada automaticamente a cada envio real à seguradora, máximo 2 renovações sem saída; "AGENTE" retoma já, "EU CUIDO" tira o agente do acionamento | EXTRA-001.4; diagnóstico §11.4. O Founder delegou o valor ("desde que caiba"); nota 60 s = 92, 90 s = 74, 120 s = 41 |
| **D-PILOTO-11** (12/09) | Fonte de verdade: **PDF** para coberturas/franquias/cláusulas/plano, **sistema de gestão** para parcelas/quitação/status/vigência — e **a arquitetura não nasce presa à InfoCap**: porta `PolicyDataProvider`, InfoCap = primeiro adaptador, Quiver/Agger/Segfy = adaptadores; seguradoras e ramos são catálogo **nosso** (chave SUSEP), nunca a lista do sistema de gestão; corretora só com PDFs também é atendida | EXTRA-001.1, 001.5; diagnóstico §7.3 |
| **D-PILOTO-12** (12/09) | **Nome do agente é escolha livre da corretora**, trocável a qualquer hora ("Amanda" na Resulta é escolha da Saionara e fica). A SPEC garante que nunca confunde: apresentação usa o nome escolhido; "especialista" nomeia a atendente real; trocar o nome não muda conversa em andamento; nome de agente ≠ nome de membro da equipe (o card recusa); nos dossiês o agente assina 🤖 | EXTRA-001.2; diagnóstico §7.4 |
| **D-PILOTO-13** (12–13/09) | Eficiência do resumo das 19h: **sinistro conta como sucesso** (coleta inicial feita + dossiê entregue); sucesso = **até enviar ao segurado a mensagem do acionamento** (protocolo, link ou agendamento); pós-acionamento fora. **Delegado e decidido em 13/09:** só "ajuda por incapacidade" (`ura_travou`, `dado_faltante`, `sentinela_esgotou`) entra no denominador; "ajuda por regra" (vítima, cliente pediu humano, valor acima do limite) fica fora e aparece como contagem própria. Nota 88 × fórmula pura 70 | EXTRA-001.3; diagnóstico §7.5 |
| **D-PILOTO-14** (12/09) | Execuções de alta qualidade sem serem exorbitantes: AAA opção B na execução, marcha fixada por SPEC (diagnóstico §8), ≤ 12 guardas novos por SPEC, bateria sobre motor e acervo real | todas as EXTRA-001.x |
| **D-PILOTO-15** (13/09) | **SIM** à SPEC retroativa EXTRA-001.0 que documenta as cinco entregas de 08–10/09 que entraram sem SPEC | EXTRA-001.0 |
| **D-PILOTO-16** (13/09, delegado) | **SPEC-101 (fábrica de conectores) vira a porta; EXTRA-002 Agger, EXTRA-008 Quiver e EXTRA-009 Segfy viram adaptadores dela** e mantêm seus números. Nota 90 × manter três SPECs independentes 55 × renumerar 40: uma porta, três adaptadores, zero motor paralelo | EXTRA-001.1 §7.3 |
| **D-PILOTO-17** (13/09, delegado) | Bradesco vidros: **primeiro uma captura no `abraseuatendimento` com o slug `bradesco`** (existe no bundle do portal); se o portal aceitar a apólice, é a rota; o `agendeseuservico` só entra se a captura provar recusa. Nota 85 × construir o `agendeseuservico` às cegas 30 × decidir sem captura 20 | EXTRA-001.10; roteiro de captura da Regina |
| **D-PILOTO-18** (13/09, delegado) | Rotina de cobrança da Resulta: modo **`equipe`** (nota 92 × `cliente` 48: exige `confirmacao_cliente`, 2 de 7 inadimplentes sem telefone, e o Founder quer a atendente validando antes de o segurado receber); **N = 7 dias** por segurado (85 × 3 dias 60 × 14 dias 70); `attendant_name` = a atendente humana da Resulta (nome confirmado pelo Founder no canário); `team_number` = TESTE-B no canário, trocado pelo número da atendente só pelo Founder depois; **a rotina só é reativada depois que o bloco implantável P0 da 001.6 (chamado "BLOCO 0" nesta decisão; na SPEC, BLOCO 0 é a medição e P0 é o implantável) estiver no ar** (reativar antes = avalanche picotada: 25) | EXTRA-001.6 |
| **D-PILOTO-19** (13/09) | Senhas novas da Allianz e da Mapfre só chegam na segunda-feira (15/09) e **isso não trava nada**: a 001.6 executa tudo; o canário dos dois portais fica em espera nomeada e fecha quando a senha chegar | EXTRA-001.6 |
| **D-PILOTO-20** (13/09) | Criação das SPECs EXTRA-001.x **neste chat (Fable)** com laço leve (redator Opus → revisor Opus → emendas → resumo ao Founder), sem AAA; **execução em chat novo por SPEC, sob AAA opção B** com a marcha do §8. Nota 91 × chat novo escreve e executa 55 × executar aqui 40 | diagnóstico §8 |

## D-E0016-01…12 · SPEC-EXTRA-001.6 — decisões tomadas por delegação na execução (14/09/2026), com nota por opção

> O Founder pediu (13/09): *"não pare para perguntar; dê nota 0–100 às opções, escolha a melhor e me avise no relatório"*. As decisões abaixo foram tomadas assim; D-PILOTO-18 e D-PILOTO-19 foram **conferidas** contra o executado e não divergem (a equivalência "BLOCO 0 da decisão = BLOCO P0 da SPEC" está escrita na proposta §5).

### Decisões da SPEC-EXTRA-001.1 (14/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09: "não pare para perguntar; dê nota às opções, escolha a melhor e me avise no relatório")

| ID | Decisão | Opções e notas | Onde |
|---|---|---|---|
| **D-E0011-00** (arquitetura) | **A porta `PolicyDataProvider` já existia** (`backend/app/providers/policy_data_provider.py`, SPEC-016 E5); o diagnóstico §7.3 mandava criar `backend/app/services/policy_provider/` — seria motor paralelo (CLAUDE.md §5). A 001.1 EVOLUIU o arquivo que existe; nenhum diretório novo | evoluir **95** × criar ao lado **5** | proposta §0.3; relatório §1 premissa 1 |
| **D-E0011-01** | `companies.llm_max_tokens` (2000 em 5/5) **não sobe** na migration | deixar **70** × subir **55** | 📊 é o fallback da `llm_factory` para TODOS os papéis; auxiliar/subagente mantêm teto baixo de propósito |
| **D-E0011-02** | o extrator documental ganha os DOIS layouts reais (HDI sem `R$`; Allianz com franquia "pct mínimo") — ESSENCIAL fora do texto da proposta | fazer no BLOCO D **90** × pendência **30** | D4: sem isso o golden 10/21 é impossível |
| **D-E0011-03** | golden reconciliado da Allianz condomínio = **21** (PDF), não 15 (cadastro); o controle do contador é fixture sintética | 21 **95** × 15 **10** | D5: Σ cadastro = 72% do `preliq`; a Allianz NÃO é controle |
| **D-E0011-04** | M-E1 usa turno sintético ≥ 128 chunks e o turno passa a gravar `rag_chunks`/`rag_chars` | sintético **80** × esperar turno real **20** | D3: o tamanho dos 2 turnos grandes não está no banco |
| **D-E0011-05** | teto do bloco recuperado = **60.000 chars** (env `TETO_DO_CONTEXTO_RECUPERADO_CHARS`), corte por TRECHO inteiro, excedente dito | 60k **86** × 120k **70** × 20k **55** | Builder E |
| **D-E0011-06** | ligação turno ↔ ferramenta por `trace_id = "<session_id>\|<client_request_id>"` (coluna e escritor que já existiam; zero DDL); ContextVar marcado antes do `create_task` | trace_id composto **88** × `client_request_id` puro **62** × chave em `input_summary` **55** | 📊 0 leitores de `trace_id`; a SPEC fica com UMA migration |
| **D-E0011-07** | `Dinheiro = Decimal`; modelo canônico no MESMO arquivo da porta; `Indisponivel` próprio (não o `UNAVAILABLE` da 094, que é `str`); `policy_catalog.py` NÃO existe (delegação direta a `coenti_de`/`cogrupo_de`) | Decimal 90 × centavos 55 · mesmo arquivo 95 × módulo 40 · próprio 92 × importar 25 · sem catálogo 95 | Builder A (D-A-01/02/03/05) |
| **D-E0011-08** | casamento de rótulo = igualdade normalizada OU grupo declarado em `rotulos_de_cobertura.json`; desempate por LMI só com 1º token comum; NUNCA substring; `Cobertura.divergencias` é tupla (Danos Elétricos diverge em franquia E prêmio); tolerância do contador R$ 0,05 | **90** | Builder A (D-A-06/07) |
| **D-E0011-09** | o conector expõe `policies_all` ao lado de `matches[:10]` intacto (a decisão de vigência fica na porta) | (b) **85** × filtrar antes de truncar **25** | Builder B (D-B-01) |
| **D-E0011-10** | o DETALHE continua vindo do `lookup` depreciado com `policy_number` (o compositor e o briefing consomem o `policy_evidence_pack` de ~40 chaves que só o conector monta); `sem_vigente` é status novo que curto-circuita o compositor; ramo pedido sem vigente NÃO filtra até zero e o motivo diz | 90 × 20 · 85 × 40 · 85 × 10 | Builder B (D-B-02/06/07) |
| **D-E0011-11** | o briefing é montado da `Apolice` RECONCILIADA da porta (origem por linha), com fallback para `coverage_sections` se a reconciliação falhar; a linha `nodes.py:273` FICA com parênteses e motivo (veredito idêntico, medido); `policy_options` só em `ambiguous_policy`/`policy_number_ambiguous` | 90 · 85 × sair 40 | Builder C (D-C-01/03/e) |
| **D-E0011-12** | Liberty = Yelum e Itaú = Porto saem do prompt e viram `familias_de_acionamento` no catálogo (seção nova; 📊 ITAU tem coenti UNKNOWN e mesmo assim aciona por `porto`: identidade SUSEP ≠ acionamento) | seção nova **90** × reusar `canonica` **40** | Builder C (D-C-05) |
| **D-E0011-13** | `vehicle` FICA no contrato, depreciado; só os 4 `hasattr` saem; `ItemDeRisco` entra no modelo, preenchido pelo adaptador; a migração dos 4 chamadores vira `P-E0011-VEHICLE-VIA-DETALHAR` | (1) **90** × migrar já **45** | Builder D (D-D-01): migrar tocaria acionamento (017) e vidros (025) fora da superfície testada |
| **D-E0011-14** | franquia em prosa casada ANCORADA no cadastro (i-ésima prosa ↔ i-ésima linha do documento cuja franquia o cadastro declara); sobras viram sinal, nunca adivinhadas; cobertura × plano decidido pelo nº de colunas de dinheiro; `assistance_plan` com preço é plano E linha; teto de `evidence_items` 40 → 60 com estruturados antes dos fragmentos | 88 × ordem pura 25 · 92 × por rótulo 20 · 90 × 35 · 85 × 30 | Builder D (D-D-02/03/04/05) |
| **D-E0011-15** | a tabela de backup da migration recebe RLS numa 2ª passada da mesma migration (advisor `rls_disabled_in_public` depois do 1º APPLY); o arquivo foi emendado para o APPLY já nascer assim | ligar **95** × deixar **5** | relatório §5 |
| **D-E0011-16** (conserto) | o cache documental decide o hit pela CONEXÃO, gravada no nome do arquivo (`documents` não tem coluna nem `metadata`; zero DDL); leitor antigo com conexão declarada = MISS, nunca hit errado; os PDFs guardados antes perdem o hit na 1ª leitura (`P-E0011-CACHE-DOCUMENTAL-SEM-CONEXAO-REAPROVEITAVEL`) | nome do arquivo **85** × coluna nova (DDL) **35** × ignorar a conexão **0** | juiz fresco ① |
| **D-E0011-17** (conserto) | FUTURA e DESCONHECIDA só são elegíveis quando não há VIGENTE; havendo, saem das opções mas o motivo as cita ("há 1 apólice que começa em dd/mm"); nunca entram no histórico oculto; a palavra "vigente" só para VIGENTE | **90** × tratar como vigente **0** × ocultar em silêncio **30** | juiz fresco ② |
| **D-E0011-18** (conserto) | o status administrativo do fornecedor FICA no briefing, em linha própria com a trava ("não decide vigência; não se repassa ao cliente"); a vigência impressa é por data | linha própria **85** × apagar **50** (perderia o sinal "não entregue ao cliente" que a corretora usa) | juiz fresco ③ |

| ID | decisão | opções e notas | efeito |
|---|---|---|---|
| **D-E0016-01** | `interpret_login` puro extraído nas 4 journeys que só classificavam dentro do `login_check` (Mapfre, Tokio, Yelum, Zurich), com os MESMOS `if` | A extrair (85) · B G3 só sobre Allianz+HDI (55) · C dirigir `login_check` com `page` falsa (40) | o guarda G3 roda o motor das 6 journeys sobre as 6 telas reais |
| **D-E0016-02** | o campo "Quem assina a mensagem" foi CRIADO na tela (não existia; a proposta dizia "ganha rótulo") e a Implantação 1 inclui o smith-web | criar (95) · preencher por SQL (20) | o Founder preenche pela tela; sem isso os modos reais ficam retidos |
| **D-E0016-03** | M3 remove as DUAS frases da Allianz (`acesso negado` e `valide os dados`), não só uma como a proposta §11 escreveu | duas (mede) · uma (o guarda ficaria verde: mutação inócua) | mutação que não muda comportamento não mede |
| **D-E0016-04** | a chamada de conversa em `_entregar_agora` continua `send_message(destino, texto, integration)` letra por letra; `bloco_unico=True` só viaja quando é documento | kwargs condicionais (90) · kwarg sempre (quebrou 2 guardas vizinhos cujos dublês não o aceitam) | os guardas 078 e governador continuam medindo o caminho antigo |
| **D-E0016-05** | `chave_do_grupo` = `empresa\|segurado\|portal` (três segmentos) | três (88) · dois como a proposta (45: o guarda de dois tenants não teria como ficar vermelho) | G7 prova que dois `company_id` nunca fazem grupo misto |
| **D-E0016-06** | N+1 passagens pelo governador por grupo (não UMA como a proposta B1.2) | N+1 e registrar (85) · kwarg novo na porta, outro dono (60) · chamar `send_*` direto (0) | `P-E0016-GOVERNADOR-POR-APROXIMACAO`; em `equipe` são 25–55 s entre componentes |
| **D-E0016-07** | em `test`, a janela de N dias lê `send_mode='test'` (vale nos dois mundos) e, se ilegível, a simulação SEGUE com blocker; a flag de demonstração desliga a janela também | seguir (88) · parar como no real (60) | o Founder ensaia o que a atendente vai receber; um ledger ilegível não mata a demonstração |
| **D-E0016-08** | o bloco de diagnóstico de sessão morta da Allianz (`:3786`) FICA além do novo antes do `return` — não era código morto: vive no ramo "logado sem tela de parcelas" | manter os dois (92) · apagar como a proposta pedia (25) · fundir (60) | nenhum comportamento real é apagado em silêncio |
| **D-E0016-09** | `unknown` pinta NÃO MEDIDO (cinza) na Central, não amarelo | NAO_MEDIDO (88) · PULSA_SEM_PRODUZIR (55) | "não verificado ainda" é literalmente não medido; o painel abre por `ehProblema()` |
| **D-E0016-10** | `verificado_em` na tela de Conectores vem de `portal_accounts.updated_at` (o carimbo do veredito), não de `portal_sessions.verified_at` | `updated_at` (85) · `verified_at` (60) | a tela e o breaker leem o mesmo relógio |
| **D-E0016-11** | o vocabulário de `health` mora em `portal_worker.worker` e `billing_collection` o IMPORTA (com fallback literal) — a cópia do B1 foi eliminada na integração | importar (85) · duas listas (10) | CLAUDE.md §5: uma lista, um lugar |
| **D-E0016-12** | o Q10 do canário (abrir os 4 portais com senha válida) só roda com `?portais=1` | opcional (90) · sempre (50: ≈2 min e 4 logins reais a cada corrida) | Q1–Q9 ficam baratos; Q10 é chamado de propósito |
| **D-E0016-13** | no timeout do `login_check` o portal é VARRIDO assim mesmo, com blocker; teto 600 s (clamp 60–900); descarte só com veredito ruim | varrer no timeout + teto 600 (88) · só subir o teto (55) · remover o prólogo (30) | juiz fresco B1: a fila real espera 144 s em média e o teto de 120 s desligava 5 de 6 portais |
| **D-E0016-14** | linhas do portal com o MESMO recibo são CONSOLIDADAS numa parcela antes de reservar (📊 a Tokio devolve 4 linhas para 1 boleto consolidado) | consolidar por recibo (90) · reservar por linha (25: 3 bloqueios falsos por execução) | lente do dado A-2 |
| **D-E0016-15** | cada Q do canário tem identidade de segurado própria; Q2/Q3 mantêm o RECIBO do Q1 para medirem a reserva, não a janela | (único caminho que faz Q5 provar a allowlist) | juiz fresco B2 |
| **D-E0016-16** | a Allianz só devolve `failed` por credencial quando NÃO há 2+ sinais de dashboard na tela | `failed` só com `hits < 2` (85) · deixar (50) | juiz fresco P5: um toast com "acesso negado" num dashboard logado abriria o breaker e mandaria trocar uma senha certa |
| **D-E0016-17** | a migration 04 redige `output_preview` (a coluna irmã que a 03 não olhou), sem rollback, pela mesma justificativa da 03 | aplicar (95) · deixar (5: PII na tela hoje) | lente do dado A-1 |

### Decisões da SPEC-EXTRA-001.2 (14/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; a proposta foi executada COMO ESTÁ, D-PILOTO-20, laço curto)

| ID | Decisão | Opções e notas | Onde |
|---|---|---|---|
| **D-E0012-01** | `TURNO_TTL_SEGUNDOS`=90, 3 renovações (📊 p90 18 s · máx 53 s de `response_time_ms` — tempo do modelo; a posse real só o canário mede, P-E0012-J11) | 90 **85** · 60 **55** · 180 **40** | relatório §1.2 premissa 5 |
| **D-E0012-02** | `atendente_de_plantao` regra (2) = exatamente um `member` ativo não-owner (📊 não existe papel `attendant`) | member **80** · criar `attendant` agora **25** (P-PILOTO-16 é 🧑) | BLOCO DF |
| **D-E0012-03** | P-PILOTO-15 pela opção b′: a pausa protege quando `claimed_at > resolvido_em` | b′ **88** · limpar `resolvido_em` **35** · ingênua **40** | BLOCO E |
| **D-E0012-04/05** | `CAMPOS_DE_CONTROLE={dados_confirmados}`; `confirmados[slot]={valor, origem, em}` com leitura tolerante | **90** / **92** | BLOCO C |
| **D-E0012-06** | o índice único da M2 só entra com 0 duplicatas abertas (havia 0); nunca fechamento em lote | **92** · fechar a mais antiga **20** | M2 |
| **D-E0012-07** | o feed do silêncio é escrito dentro de `a_ia_deve_calar`, memo por classe/dia | **85** | BLOCO E |
| **D-E0012-08** | escopo vazio na trava de turno → recusa fail-closed (nunca chave global) | **92** · chave global **30** | BLOCO AB |
| **D-E0012-09** | visão/transcrição rodam dentro do turno | **90** · no recebimento **55** | BLOCO AB |
| **D-E0012-10 → 16** | janela 3·8·18 (nota 94) REVISTA depois do painel: 18 s SÓ com conectivo; sem pontuação = 8 s | conectivo-só **90** · 18 para tudo **20** · 15 para tudo **50** | J1 + lente |
| **D-E0012-11/12** | re-planejamento antes de gravar (teto 2); sem `delay` no `/send/text` | **88** / **85** | BLOCO AB |
| **D-E0012-13** | teto de tamanho DUPLO: 3 frases E 450 chars (📊 p90 431) | **92** · só frases **40** | BLOCO DF |
| **D-E0012-14** | a recusa de nome colidente mora no `PATCH` do Next (quem grava `attendant_name`) | **85** · FastAPI **30** (P-E0012-D4) | BLOCO DF |
| **D-E0012-15** | o bloco de memória não é filtrado por assunto; o prompt desaconselha (P-E0012-D1) | **70** · suprimir memória **45** | BLOCO DF |
| **D-E0012-17** | posse perdida antes do envio devolve os itens ao buffer; `renovar_turno` antes de gerar/regenerar/enviar | **92** · `return` seco **0** | conserto J2 |
| **D-E0012-18** | J4 sem migration M3 (📊 0 linhas divergentes); 23505 relido nos dois resolvedores | **90** · M3 no-op **20** | conserto J4 |
| **D-E0012-19** | uma regeneração por turno entre os fiscais; metadados preservados | **90** · encadear **30** | conserto J8 |
| **D-E0012-20** | `ancoras_de_pergunta_por_slot.json` mora em `app/resources/` | **92** | conserto J9 |
| **D-E0012-21** | `apresentado_em` só depois do envio confirmado e se o texto enviado se apresenta | **92** · marcar em `agent_node` **70** | conserto J5 |
| 🧑 **caixa** | o nome do agente da Resulta (D-PILOTO-12); `PRESENCA_DIGITANDO_LIGADA=true` depois do canário; papel `attendant` (P-PILOTO-16) | — | Founder |


## D-PROTO-01…06 · O protocolo de execução vira AAA FAST (v12) — 16/09/2026

> Auditoria completa em `docs/canon/specs-propostas/AUDITORIA-PROTOCOLO-AAA-2026-09-16.md` (📊 transcritos reais do Claude Code, não os relatórios). Founder em 16/09: *"se você concluiu que esse é o melhor protocolo, podemos tentar; quero as duas comparações da 001.3 e 001.4 para você verificar depois"*.

| ID | Decisão | Opções e notas | Onde |
|---|---|---|---|
| **D-PROTO-01** | **AAA FAST (protocolo v12) é o DEFAULT de execução** de toda SPEC a partir da EXTRA-001.3: UM executor Opus 5 numa sessão NOVA por SPEC (sem orquestrador), provas mecânicas, UM juiz fresco read-only (Fable 5.1 em CRÍTICO, Opus 5 em PADRÃO, nenhum em LEVE), UM conserto, entrega. O AAA completo (painel de 3 lentes + red team + lente + confirmação, v11.2) vira **ESCALAÇÃO por gatilho** (v12 §8). Supera D-PILOTO-14 ("AAA opção B na execução") e a segunda metade de D-PILOTO-20 ("sob AAA opção B"); "chat novo por SPEC" continua. O laço curto (diagnóstico §13.7, opção C) fica **superado** | FAST **89** (alvo) · laço curto real 52 · AAA completo 48 · Opus só sem juiz 74 | AUDITORIA §4, §9, §11 |
| **D-PROTO-02** | **Teste A/B nas próximas 3 SPECs**, com a regra de decisão escrita ANTES: 001.3 = Opus 5 `xhigh` + juiz Fable 5.1 · 001.4 = Opus 5 `max` + juiz Fable 5.1 · uma PADRÃO (001.5 ou 001.7) = Opus 5 `high` + juiz Opus 5. Métricas pelo script (D-PROTO-04). FAST fica como default se: custo ≤ 50 % da linha de base (001.6/001.1/001.2) por marcha · relógio ≤ 2h30 em CRÍTICO (ou 2 fatias ≤ 1h15) · defeitos no canário do Founder ≤ os da base · o juiz não reprovou 2×. Se o canário falhar numa SPEC de envio → lente do dado e confirmação entram no padrão CRÍTICO (não o AAA inteiro). Se o custo falhar com o canário ok → baixa-se o teto de turnos, nunca se sobe o de agentes | — | AUDITORIA §8 |
| **D-PROTO-03** | **O Fable audita cada execução do A/B DEPOIS**, no chat de decisão, read-only, ≤ 30 min, sem subagente: roda o script, lê o relatório, amostra 3 números e 3 trechos do diff, compara com a base e escreve a nota do A/B. Não substitui o canário do Founder (o único juiz que não mente). Depois do A/B, a auditoria do Fable passa a ser por LOTE de SPECs, não por SPEC | por SPEC durante o A/B **90** · nunca **30** · sempre **55** (custo Fable sem ganho medido) | — |
| **D-PROTO-04** | **Tetos em TURNOS e CONTEXTO**, aplicados por env e hook (`.claude/settings.json`: `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=2`, `..._SPAWN_DEPTH=1`; `.claude/hooks/teto-de-agentes.py` bloqueia o 5º agente da sessão). "Tokens de subagentes" deixa de ser grandeza de relatório: 📊 o número do Agent map é o CONTEXTO FINAL do agente, não o consumo; o consumo é turnos × contexto, medido por `backend/scripts/medir_execucao_claude_code.py` e colado no relatório (8 linhas, v12 §11) | — | AUDITORIA §2.1, §5 |
| **D-PROTO-05** | **Documentos:** proposta ≤ 40 KB para execução (as de 96–124 KB já escritas são executadas lendo §0 + as unidades, apêndices sob demanda); relatório ≤ 15 KB no `SPEC-EXECUTION-REPORT-TEMPLATE-FAST.md`; PENDENCIAS/DECISIONS/ADDENDA numa passada, um commit; dossiê republicado pelo Fable, fora do caminho crítico | — | AUDITORIA §2.4, §7 |
| **D-PROTO-06** | **O aquecimento do executor é** CLAUDE.md + a memória do projeto (entra sozinha na sessão) + a proposta (§0 e unidades) + o BLOCO 0 sobre os arquivos que vai tocar (ler da linha 1, traçar chamadores). **Nenhuma sessão executa duas SPECs**: 📊 a sessão que executou 001.6/001.1/001.2 chegou a 963 k de contexto, comprimido 2× por "continuação" — o que parecia aquecimento era resumo, e custou ≈ metade de cada SPEC | sessão nova **88** · uma sessão por 2–3 SPECs **35** · sessão nova + documento de contexto extra **60** (bloat) | AUDITORIA §2.2 |

### Decisões da SPEC-EXTRA-001.3 (16/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; AAA FAST, D-PROTO-01)

| ID | Decisão | Opções e notas | Onde |
|---|---|---|---|
| **D-E0013-01** | Segunda migration, não prevista na §13: `work_events.work_run_id` deixa de ser `NOT NULL`. 📊 Sem ela, `_anotar_no_diario` levanta `NotNullViolation` dentro de um `except` que engole — e o outcome *"todo envio contado"* é impossível por construção | migration **88** · diário em `agent_activities` **55** · `work_run` sintético **35** | `20260916_02` · relatório §3 |
| **D-E0013-02** | A captura de número da casa é marcada em `source = "live_interno"`, sem coluna nova | sem migration **80** · coluna nova **70** · continuar descartando **20** | `attendance_capture.py` |
| **D-E0013-03** | O casador de telefone do BFF é uma PORTA declarada em TS, confrontada com o motor Python caso a caso (G-B3) | porta com guarda cruzado **80** · chamar Python na Fila **30** · duplicar sem guarda **40** | `lib/atendimento/numeros-da-casa.ts` |
| **D-E0013-04** | O gate de ligar o agente mora no BACKEND (`/api/atendimento/pode-ligar`, pelo `resolver_destino_de_suporte`) e o painel pergunta | backend **90** · duplicar a resolução no BFF **40** · só `human_support_destinations` no BFF **60** | BLOCO F |
| **D-E0013-05** | Falha de comunicação com o backend DEIXA ligar (fail-open no gate), enquanto `attendance_agent_active` segue fail-closed no runtime | fail-open no gate **85** · bloquear por indisponibilidade **35** | `porteiro-de-ligar-o-agente.ts` |
| **D-E0013-06** | `channel_status` vazio deixa ligar; só o estado explicitamente desconectado barra | **85** · barrar no vazio **40** | `porteiro_do_agente.py` |
| **D-E0013-07** | A régua de língua humana roda nos quatro modelos SEM a cláusula *"termina numa próxima ação com dono"* — ela é regra da CARTA ao segurado, não do dossiê que a atendente lê | **85** · aplicar inteira **45** (reprovaria os quatro por desenho) | G-D1 |
| **D-E0013-08** | `weekly_report`/`proactive_suggestions` ficam fora (§2 da proposta) e viram pendência, em vez de entrar de carona | **80** · absorver agora **50** (dois envios semanais sem gate próprio) | P-E0013-01 |

| **D-PROTO-07** (16/09, auditoria do Fable sobre a 001.3 — experimento A) | 📊 medido no transcrito `fa5d41c4`: executor 318 turnos · pico **726 k** · 142 M tokens de contexto · US$ 84 (o relatório, fechado antes dos 2 últimos commits, dizia 271 · 649 k · US$ 66) · juiz Fable 26 turnos · US$ 7 · lente US$ 3 · **total US$ 94** · relógio **3h57** de sessão (2h47 até o relatório) · 2 agentes · gates verdes reproduzidos (6 guardas rc=0). Contra a 001.2 (laço curto: 5h03, ≈ US$ 175–200 com o orquestrador): **−22 % relógio · ≈ −50 % custo**, qualidade igual ou melhor (juiz Fable 3 blockers exclusivos; triagem por diff 4 regressões, 1 de produto). **Decisões:** (1) os tetos de 250 turnos / 300 k **ficam** — a segunda fatia rodou a 400–726 k na mesma sessão e custou ≈ o dobro do que custaria em sessão nova; a regra escrita não bastou, então vira **hook** (`.claude/hooks/teto-de-contexto.py`: acima de 300 k, aviso a cada edição) e o prompt da 001.4 manda fechar a fatia 1 e abrir sessão nova, sem exceção; (2) relatório: **alvo 15 KB, teto duro 25 KB** em CRÍTICO quando o excesso for medição (o da 001.3 tem 24,7 KB e é todo medição); (3) a suíte inteira roda **uma vez, depois do conserto, sozinha** — 📊 rodou em paralelo com o juiz e levou 57 min contra 24 na base; (4) critério (b) do A/B (≤ 2h30) **não foi atingido** na 001.3; (a), (d) sim; (c) depende do canário do Founder. O A/B segue para a 001.4 | manter tetos + hook **90** · subir teto para 700 k **25** (o custo é o contexto) · sem hook **40** | relatório da 001.3 §10; `medir_execucao_claude_code.py --sessao fa5d41c4` |

### Decisões da SPEC-EXTRA-001.4 — fatia 2 (17/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; AAA FAST, D-PROTO-01; D-E0014-01…05 estão no relatório da fatia 1)

| ID | decisão | opções e notas | onde |
|---|---|---|---|
| **D-E0014-01** | slot `*_opcao` VAZIO numa tela reversível continua indo ao Cérebro (desenho de 19/08), agora com as opções numeradas da tela no prompt; `needs_human` só para a tecla que decide o RAMO (`ramo_indeterminado`) e para `sem_chute`. Palavra que casa 0 opções segue a mesma regra; 2+ → `tecla_ambigua` | Cérebro + opções **88** · `needs_human/slot_opcao_sem_derivacao` geral, como a proposta §5.2 regra 3 **35** (reintroduz o travamento de 19/08 em 29 slots — o oposto do outcome) · `needs_human` reentrável **40** | relatório da 001.4 §1 |
| **D-E0014-02** | `MAX_TENTATIVAS_POR_TELA = 2` · `MAX_TENTATIVAS_NA_SESSAO = 6` (env, com default). 📊 telas órfãs que pedem algo, distintas por sessão, no corpus de 17/09: 71 sessões · p50 **2** · p90 **12** · máx 62; **61/71 (86 %) ≤ 6** — a cauda é conversa humana longa, que deve ir a uma pessoa | 6 **85** · 12 (p90) **70** (o dobro de chamadas ao Cérebro em sessão que já vai mal) · 2 por sessão, o de hoje, **30** (é o defeito de 10/09) | relatório da 001.4 §1 |
| **D-E0014-03** | teto de guardas: fundir GA-2+GA-3 e GB-1+GB-2+GB-3; GA-1 dentro do guarda existente — fatia 1 cria **2** arquivos | fundir **88** · 13 arquivos com addenda **55** | relatório da 001.4 §1 |
| **D-E0014-04** | 🧑 **o Founder decidiu (17/09) rodar a fatia 1b nesta mesma sessão**, "para aproveitar o contexto", contra a regra de sessão nova (D-PROTO-07). Contexto da 1b: ~300 → ~530 k. A fatia 2 volta a sessão nova | decisão do Founder — registrada para a auditoria do A/B | relatório da 001.4 §1 |
| **D-E0014-05** | o hub carrega `cartographer` e `atlas.weaver` pelo CAMINHO quando o pacote `app.services` foi montado à mão — 📊 75 testes fazem isso e `test_spec017` quebrou na 1ª rodada; é o mesmo arquivo, nunca uma cópia do parser | carregador **82** · import tardio com `except` que desliga a camada 1 em silêncio **30** · pré-carregar nos 75 testes **40** | relatório da 001.4 §1 |
| 🧑 **D-E0014-06** | **O Founder mandou terminar a fatia 2 nesta sessão** ("EXECUTE A FATIA 2 ATÉ O FINAL… POR VC"). O hook de contexto avisou acima de 300 k desde a primeira edição (a leitura integral pedida levou a sessão a ~420 k antes do código) | decisão do Founder — registrada para a auditoria do A/B (D-PROTO-03) | relatório §10 |
| 🧑 **D-E0014-07** | **Decisão do Founder (17/09): `qual_seguro_opcao` vem do RAMO DA APÓLICE.** Execução: a família do ramo (`resi`/`cond`/`empr`, `policy_data_provider.familia_de_ramo`) vai da apólice localizada (InfoCap → `nodes.py` → ferramenta) ao motor, que grava o RÓTULO ("Residencial"…) e `resolver_tecla` o converte no dígito LENDO A TELA; o ramo vence a palavra da atendente; a dedução pelo relato (fatia 1) saiu. Sem apólice localizada, o agente pergunta o ramo JUNTO com a apólice; sem ramo nenhum, a tela vai a uma pessoa (trava) | rótulo lido na tela **90** · dígito fixo por ramo **70** (a ordem do menu não é garantida) · manter o relato como reserva **40** (chute sobre o ramo foi o defeito da SPEC-083) | `insurer_dispatch_service.rotulo_do_ramo_da_apolice` |
| **D-E0014-08** | AGENTE / EU CUIDO valem do **número de suporte**, de um **número da casa** (privado) e do **grupo** de suporte. 📊 Toda instância nasce com `ignoreGroups: True` (`pairing_orchestrator.py`, `whatsapp_channel.py`, `admin_atlas.py`): hoje a palavra digitada NO GRUPO não chega. A mensagem só vale se FOR a palavra, e só com UM acionamento elegível na corretora | três origens **85** · só o grupo **30** (nunca chegaria) · ligar grupos na instância **35** (todo grupo do número da corretora entra no webhook, limitado a 240/min) | `dispatch_router.ler_palavra_da_equipe` · P-E0014-06 |
| **D-E0014-09** | A pergunta ao segurado (D3) espera **na sessão**, com prazo do **Vigia**; nenhuma linha em `work_waits` | sessão + Vigia **85** · `work_waits` **50** (exige a conversa do segurado, que a sessão não tem, e o leitor de `work_waits` dispara `espera.vencida` ao GRUPO) | proposta §3.1 |
| **D-E0014-10** | `FILA_ALERTA_S = 1200` (📊 Allianz: p90 10,5 min até a 1ª fala) e o alerta da fila vira evento/linha do resumo, como a 001.3 fez com `human_silent_alert`; "um instante" à seguradora a cada **60 s**, no máximo **2** (📊 Allianz encerra com 103 s no pior caso; a atendente de 10/09 encerrou 158 s depois de se apresentar) | 1200 s **85** · 600 s **50** (cutucaria fila vazia) · holding 60 s × 2 **82** · 90 s **55** (passa dos 103 s com o ciclo de 20 s) | `dispatch_watchdog.py` · `dispatch_router.py` |
| **D-E0014-11** | A âncora POSITIVA (`FRONTEIRAS`) entra; a passagem à fase humana POR EXCLUSÃO fica (é o caminho do Cérebro nas telas não mapeadas) | as duas **85** · só a positiva **40** (as 378 telas cegas ficariam sem Cérebro) | `handle_insurer_message` |
| **D-E0014-12** | porto-auto: sai o passo `complemento` do corpo ("não tem"), que sombreava o do tronco (`{local_complemento}`) | tirar o passo morto **75** · padrão "não tem" no motor **70** · manter **20** | `corridor_playbooks.py` |
| **D-E0014-13** | azul `menu_atendimento` responde pelo RÓTULO "Novo serviço" (a variante numerada tem 0 ocorrências desde 26/12/2025; se voltar, o reparo da fatia 1 converte a palavra recusada no dígito) | rótulo **80** · manter "1" **35** (numa variante, 1 = Cancelar serviço) | idem |
| **D-E0014-14** | A pausa segue a **D-PILOTO-10** (abre + 2 renovações; a 4ª fala não renova). A proposta §7.4 escreve "terceiro → não renova": a decisão do Founder vence o texto | lei **90** · texto da proposta **40** | `abrir_ou_renovar_pausa` |
| **D-E0014-15** | `test_spec038_sentinela.py` é do **Sentinela de Rotas** (SPEC-038 C, drift) e já chama o motor dele; não é o Sentinela do acionamento. Nada muda nele; o do acionamento é exercitado por GB, GC e GD | registrar **85** · reescrever **20** | proposta §9.3 |
| **D-E0014-16** | Guardas: a fatia 2 cria **2** arquivos (GC-1…3 + GT fundidos; GD-1…4 + D3 fundidos); a SPEC fica com **4** arquivos novos (teto 12); homônimos e origem do ramo entram em guardas existentes | fundir **88** · um arquivo por linha da tabela **50** | relatório §2 |

| **D-PROTO-08** (17/09, auditoria do Fable sobre a 001.4 — experimento B) | 📊 a regra "fatia 2 em sessão nova" (D-PROTO-07) **falhou e foi revogada**: a 001.4 rodou em 3 chats (1a só lendo, 300 k antes da 1ª linha; 1b 142 turnos · 577 k · US$ 41; fatia 2 264 turnos · **902 k** · US$ 109 com 4 agentes) — ≈ US$ 175 e ≈ 5–6 h de executor, mais de 12 h de relógio do Founder entre chats: **o custo do laço curto, com incômodo a mais**. Causa: cada sessão nova paga a leitura fria da proposta de 113 KB, e o teto de contexto foi ignorado de novo por ordem do Founder. **v12.1:** UMA sessão por SPEC, do card ao push; o executor constrói a fatia 1 e delega as seguintes a UM builder subagente fresco (Opus 5 xhigh, sequencial); hook de contexto passa a pedir o builder, não a sessão nova; teto de agentes 7; toda SPEC ganha uma **FICHA ≤ 15 KB** que o executor lê no lugar da proposta inteira; as propostas restantes recebem a linha "nomes históricos" para matar a confusão v11.2/opção B/laço curto. Resultado do A/B em 3 execuções: FAST **um chat** (001.3) = melhor custo (US$ 94) e relógio (3h57) com qualidade igual; FAST **fatiado** (001.4) = custo do laço curto; laço curto (001.2) = 5h03 e ≈ US$ 175–200 | uma sessão + builder por fatia **90** · uma sessão sem builder (001.3 puro) **80** · Fable orquestrador + builders (laço curto) **55** · sessão nova por fatia **20** | `medir_execucao_claude_code.py --sessao 4ad8f447 --sessao 68460dfc` |

| **D-PROTO-09** (17/09, Founder) | **Fable 5.1 é o juiz de toda execução** (PADRÃO e CRÍTICO; LEVE só provas mecânicas) e o builder é **Opus 5 xhigh** (max só a pedido). **Modo GERENTE** vira o padrão: o Fable, no chat de decisão, monta o pacote, delega cada fatia a um builder Opus fresco, chama o juiz Fable, manda o conserto ao mesmo builder (contexto quente) e empurra; **2–3 SPECs por chat** enquanto o gerente ficar ≤ 600 k. 📊 Medido no acabamento 001.3/001.4 (17/09, este chat): builder 45 min + juiz 17 + conserto 18 + confirmação 7 + conserto 9 ≈ 1h40 de execução, 3 blockers reais do juiz e 1 da confirmação fechados, o Founder sem trocar de chat. 📊 Cache read do Fable custa US$ 0,25/M contra 0,50/M do Opus: um gerente Fable de 600 k custa por turno o mesmo que um Opus de 300 k — o orquestrador de 963 k da 001.2 custava pelos 347 turnos, não pelo modelo | gerente Fable + builder Opus + juiz Fable **92** · chat Opus solo + juiz Fable (001.3) **85** · Opus + juiz Opus **60** | v12.2 |
| **D-PILOTO-21** (17/09, Founder — produto) | **A atendente não aprende palavra nenhuma.** Na conversa com a URA: 1 fala manual = o robô espera **15 s** e continua lendo a tela atual; 2 falas em 15 s = a atendente assumiu, o robô sai daquele acionamento **em silêncio** (nada ao grupo, nada ao segurado). AGENTE/EU CUIDO ficam só como atalho opcional. **"Um instante" à seguradora só com PESSOA**; com robô, nada sai. Antes de perguntar ao segurado, o **Cérebro** tenta com o que já existe (ficha, apólice, conversa) e só aceita valor com **prova de origem**; a pergunta nunca é trivial nem repetida; tudo que faltou vira rastro `acionamento.dado_faltou` (semente de uma SPEC de aprendizado do corredor); prazo vencido → pessoa pela porta única; resposta tardia entra no slot ou é levada à URA se ela estiver na tela | — | acabamento 001.3/001.4 (`5a77366`) |

### Decisões da SPEC-EXTRA-001.5 (17–18/09/2026, tomadas pelo GERENTE com nota 0–100 — regra do Founder de 13/09; AAA FAST v12.2, modo GERENTE, experimento C do A/B)

| ID | decisão | opções e notas | onde |
|---|---|---|---|
| **D-E0015-01** | **Plano único da condição geral:** quando existe EXATAMENTE UM plano publicado para seguradora × ramo × produto, vigente na data de emissão, E o processo SUSEP da apólice casou com o documento DAQUELE plano, o plano é `contratado` com `origem='plano_unico_da_condicao_geral'`, `confianca='media'`. Com ≥ 2 planos ou sem o elo SUSEP → `nao_sabemos_ainda` (M-B4 continua: nunca o nível 1 por default) | regra com as 3 travas **85** · manter `nao_sabemos_ainda` (📊 25/38 planos chamam-se "Plano único" e nunca casariam por nome) **40** | `cobertura_e_assistencia.py::identificar_plano` · M-B4 [5] |
| **D-E0015-02** | Marcha: a soma dá **CRÍTICO** (RISCO 8: a resposta sai pelo WhatsApp); a marcha fixada (D-PROTO-02) era PADRÃO. Executada com o ELENCO do crítico (juiz Fable + lente do dado + confirmação §6.1 disparada) e o piso em 2 pontos (migration ② e o texto ao segurado), tetos por fatia de PADRÃO | elenco crítico **88** · PADRÃO puro **60** · parar para perguntar **10** | relatório §0.0/§1 |
| **D-E0015-03** | A Skill nasce como MÓDULO em `app/services/skills/cobertura_e_assistencia.py` (o lugar das Skills), chamada pelo caminho vivo (`policy_answer_composer`), com a release `insurance.cobertura_e_assistencia 1.0.0` registrada pelo `SkillRegistry` (inerte até `TOOL_GATEWAY_MODE` ligar). Nenhuma tool nova em `graph.py` | módulo + composer + release **88** · tool nova ao lado **10** (duas portas para a mesma pergunta) | fatia 2 |
| **D-E0015-04** | Todas as 3 fatias delegadas a builder Opus 5 xhigh fresco (o gerente não construiu a fatia 1); investigador do BLOCO 0 em Opus | delegar tudo **90** (protocolo §5.2 + Fable a 91 % da cota semanal, pedido do Founder de 17/09) · gerente constrói a fatia 1 **50** · investigador Opus **85** × Sonnet **65** | relatório §0.0 |
| **D-E0015-05** | A bateria inteira rodou UMA vez em 2º plano em paralelo ao juiz (antes do conserto); depois do conserto rerodaram-se os 13 guardas e a regressão dirigida, não a suíte | paralelo + afetados **85** (poupa 37 min de relógio) · suíte 2× **50** | relatório §6 |
| **D-E0015-06** | RLS ligada SEM policy nas duas tabelas novas, como as 4 globais irmãs (`normative_documents`, `normative_document_versions`, `portals`, `ura_maps`); leitura só por service role | seguir as irmãs **85** · policy de leitura `authenticated` **50** (segundo caminho de acesso) | migration ① |
| **D-E0015-07** | `vigencia_inicio` do plano = `effective_from` da versão do documento (não a data da rodada); documento sem vigência é PULADO; nível não contíguo é RECUSADO, não renumerado (renumerar mudaria em silêncio a ordem dos pacotes que a CG declara) | **85** × renumerar **40** | conserto único |
| **D-E0015-08** | `revisado_por` sem FK para `users_v2` (tabela global × usuários por corretora); validado como uuid no backend | **80** × FK **55** | migration ① · conserto |
| **D-E0015-09** | **Troca de gerente no meio da SPEC:** o gerente Fable 5.1 esgotou a cota semanal logo após o conserto único (a confirmação §6.1 morreu com HTTP 429). Um gerente **Opus 5** assumiu o MESMO chat, refez a confirmação com **juiz Opus fresco** (divergência de D-PROTO-09, que fixa Fable como juiz), fechou o relatório e empurrou. Nenhuma fatia reconstruída, nenhum builder rechamado | seguir no mesmo chat com Opus **90** · esperar a cota reabrir (sábado) **35** (a SPEC ficaria aberta 3 dias, contra CLAUDE.md §9) · fechar sem confirmação **20** (o juiz achou blocker no texto ao segurado: §6.1 obriga) | relatório §0.0 e §5 |
| **D-E0015-10** | O relatório fechou com **19,3 KB** contra o teto de 15 KB do protocolo §1. Mantido: cortar para caber exigiria remover a evidência por comando que o §0.4 obriga (juiz + lente + confirmação + BLOCO 0 numa SPEC de 3 fatias) | manter e declarar **85** · cortar evidência **45** · dividir em dois arquivos **30** (o guarda lê um arquivo só) | este relatório |

### Decisões da SPEC-EXTRA-001.5.1 (19/09/2026 — gerente, com nota 0–100; AAA FAST v12.2, modo GERENTE)

| ID | decisão | opções e notas | onde |
|---|---|---|---|
| **D-E00151-01** | Executar no MESMO chat da 001.5 (11 agentes já gastos), com o teto do hook a 24 | mesmo chat **90** × abrir chat novo **60** (perderia o contexto da 001.5 inteira) | Founder, 19/09 |
| **D-E00151-02** | O padrão do hook `teto-de-agentes.py` foi de 12 para 24 **só nesta SPEC**, por autorização escrita do Founder, depois de eu afirmar sem conferir que a variável já estava no `settings.json`. **Voltou a 12 no fechamento** | autorizar e declarar **85** × parar a SPEC **30** | §13 |
| **D-E00151-03** | O teto do aviso 🆘 passou a ser 1 por lacuna **por conversa** por dia (era por corretora): o 2º segurado do dia a quem se prometeu resposta gera o aviso dele | por conversa **88** × por corretora **60** (promessa sem dono) × sem teto **20** | `lacunas_de_conhecimento.chave_do_marcador` |
| **D-E00151-04** | Três reprovações com blocker material disparam AAA COMPLETO (§8). Em vez do painel de 3 lentes + red team, que a cota de agentes não comportava, fiz **rodadas dirigidas com caminho de saída explícito** (autorizei desmontar a flag) + julgamento final a cada uma | escalada dirigida **85** × painel completo **60** × fechar com a flag insegura **10** | §5 |
| **D-E00151-05** | No **PEDIDO** de serviço o veredito INFORMA e não FISCALIZA (`assistencia_da_base` fora de `required_facts`): quem decide acionamento é a seguradora, e uma linha extraída não pode fazer o atendente recusar socorro. Mitigação: o briefing manda não prometer o serviço quando a base nega | informar **92** × fiscalizar só a direção `nao` **60** | `infocap_tool` · rodada 2 |
| **D-E00151-06** | Manter a flag `encerrar_com_o_rascunho` em vez de desmontá-la, porque B1/B2/B3 eram obrigatórios nos dois caminhos — desmontar não economizava superfície, só trocava garantia determinística por esperar que o modelo obedeça ao briefing, sem medição de obediência | manter e consertar **90** × desmontar **70** | rodada 3 |
| **D-E00151-07** | `nodes.py` passa a IMPORTAR `SEPARADOR_DA_JANELA` da tool, em vez de manter duas literais independentes | acoplar **90** × corrigir só o comentário **65** | rodada 5 |
| **D-E00151-08** | Os 3 serviços presos sob plano pai em `rascunho` ficam onde estão e serão reextraídos: dois deles têm como "plano" uma COBERTURA, e promovê-los poria o mesmo produto em duas caixas | reextrair **85** × promover o pai **35** | P-E00151-07 |

### Decisões da SPEC-EXTRA-001.5.2 (20/09/2026 — protocolo e execução)

| ID | decisão | opções e notas | onde |
|---|---|---|---|
| **D-PROTO-10** (20/09) | **O núcleo do AAA v13 entra em TESTE**, e a EXTRA-001.5.2 foi a primeira SPEC a usá-lo: **O FIO** (a prova afirma sobre o dado GRAVADO e sobre o que a fila DEVOLVE, não sobre a função solta) + **juiz generalista ‖ red team em paralelo** + **trava de 2 rodadas** de julgamento. 📊 Medido nesta SPEC: 1 rodada bastou · 7 achados materiais, 4 exclusivos do red team ou do juiz · ≈ 110 min do card ao conserto · ≈ US$ 33 de agentes contra a média medida de US$ 146 por SPEC. Fica em teste — a decisão de virar default depende de mais SPECs | aprovar para teste **90** × manter o v12 puro **55** (o red team achou 4 blockers que o juiz não viu) × promover a default já **40** (uma SPEC não é amostra) | relatório da 001.5.2 §0/§3 |
| **D-PROTO-11** (20/09) | **O teto de agentes por sessão é 24**, e o hook `.claude/hooks/teto-de-agentes.py` não volta a 12 no fechamento de SPEC. 📊 O teto tinha sido "restaurado" para 12 ao fechar a 001.5.1 (D-E00151-02) e **travou a sessão da 001.5.2 no meio**, custando a confirmação por 3º juiz (§6). Elenco fixado junto: **builders = Opus 5**, **Fable só julga e gerencia**, **nenhum Haiku**, e **Sonnet só para volume óbvio** (trabalho mecânico e repetitivo, sem julgamento) | 24 fixo + comentário proibindo restaurar **90** × voltar a 12 a cada SPEC **30** (já custou uma confirmação) × sem teto **20** | `.claude/hooks/teto-de-agentes.py` |
| 🧑 **D-E00152-01** (20/09, Founder) | **A base de planos é escrita por LEITORES do plano Claude, não pela API do produto:** escritor Opus lê as páginas e escreve com trecho literal → a **máquina** recusa a linha cujo trecho não existe na página citada (📊 477/477 passaram) → um **segundo leitor** Opus, que não escreveu, confere todas as linhas → publicação com o **Founder como revisor**. O extrator por API deixa de ser o caminho oficial para documento novo, e o Founder **não porá crédito na chave** para isso. 📊 Resultado: 492 serviços em 108 planos e 8 seguradoras num dia, 0 chamada de API de modelo, 8 linhas retidas | leitores do plano **92** (o outcome de negócio fecha hoje, e o segundo leitor pegou 8 classes de erro grave antes de publicar) × pôr crédito e esperar o extrator **50** (📊 recall 4/27, custo recorrente) × ficar nas 23 linhas **10** | relatório da 001.5.2 §10 · P-E00152-12 |

### Decisões da SPEC-EXTRA-001.7 (20/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; núcleo do AAA v13 em teste, D-PROTO-10)

| # | decisão | notas | onde |
|---|---|---|---|
| **D-E0017-01** | **Construir o INSTRUMENTO agora e deixar os 3 dias para o Founder** (opção A do prompt). 📊 Os agentes de atendimento estão desligados nas duas corretoras e o canário da 001.5.2 não rodou; o instrumento é provado sobre o dado que já existe | A **90** × pular para a 001.10 e voltar depois **45** (a 001.10 também espera captura da Regina, e o piloto sem régua repetiria 09–11/09) | relatório da 001.7 §1 |
| **D-E0017-02** | **Dimensão sem escritor sai "NÃO AVALIADA" — não se cria proxy nem escritor dentro desta SPEC.** "Apólice certa em 1 rodada", "sabe calar" e 5 dimensões do chat não têm fonte durável | pendência escrita **80** × criar o escritor agora **55** (toca o caminho do atendimento: piso CRÍTICO, fora da faixa) × proxy por SELECT **10** (nota inventada com cara de medida) | P-E0017-03 · P-E0017-04 |
| 🧑 **D-E0017-03** (FECHADA 20/09) | **Os cortes do veredito do piloto**: proposta 💭 — nada medido abaixo do palpite de 12/09 · "aciona" com ≥ 5 casos e nota ≥ 70 · "sabe pedir ajuda" ≥ 90 · "errou a apólice" em ≤ 1 de cada 10 na folha das atendentes | decide o Founder; até lá a régua publica a nota e não o veredito | `SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md` § P4 |
| 🧑 **D-E0017-04** (FECHADA 20/09) | **Os escritores que faltam entram ANTES dos 3 dias?** Sem eles, 3 das 6 notas do atendimento dependem da folha da Saionara e da Regina. Recomendação da execução: **piloto já, com a folha** (o piloto também mede o que vale gravar) | piloto já com a folha **78** × SPEC pequena de escritores antes **70** (adia o piloto ~1 dia e toca o caminho do atendimento às vésperas dele) | P-E0017-03 |
| **D-E0017-05** | **`--modo piloto` × `--modo canario` no checklist**: a allowlist de entrada preenchida é o certo num ensaio e um desastre no piloto real; quem roda declara qual é a rodada | modo declarado **94** × adivinhar pelo tamanho da lista **40** × ignorar a allowlist **0** (era o defeito B5) | `conferir_o_que_esta_no_ar.py` |
| **D-E0017-06** | **Leitura que falha ⇒ NÃO AVALIADA na dimensão e "NÃO LIDO" na célula e na prosa** — nunca zero. E a velocidade do chat usa o p90 do PERÍODO, não do pior dia | NÃO LIDO **95** × publicar com asterisco **40** · p90 do período **92** × piso por dia **70** | `medir_o_piloto.py` |

### Decisões de 20/09/2026 — o rito, os cortes do piloto e a fila de pendências

| # | decisão | notas | onde |
|---|---|---|---|
| **D-PROTO-12** (20/09/2026) | **O núcleo do AAA v13 é o ÚNICO rito de execução a partir da EXTRA-001.10** — deixa de ser "em teste" (D-PROTO-10). O rito: **O FIO** + o teste do fio como **1ª entrega** · builders Opus 5 em **PARALELO quando os arquivos são disjuntos** · **julgamento paralelo UMA vez** (juiz generalista ‖ red team, Fable 5.1, cegos um ao outro) · **conserto único** · **confirmação curta** só se houve blocker · **trava de 2 rodadas** (`rodada_do_juiz.py`) · **bateria só DEPOIS do conserto**, triada **NOMINALMENTE** contra `docs/canon/reports/BATERIA-LINHA-DE-BASE.txt`. 📊 Medido em 2 SPECs: **001.5.2** ≈ 110 min e ≈ US$ 33 (7 defeitos materiais antes do push) · **001.7** = 151 min e ≈ US$ 47 (7 defeitos materiais antes do push; juiz 62 ‖ red team 58 → confirmação 86) — contra a média medida de **US$ 146 e 4,7 h por SPEC** nas 19 anteriores. **Cinco ajustes entram junto** (lições da 001.7): **(a) LENTE DO DADO no gate do builder** — todo número publicado é conferido por um caminho independente antes do juiz (📊 a 1ª medição publicava 3 conversas onde havia 53: o dublê nasceu do mesmo filtro do código); **(b) GATE DO AMBIENTE DE USO** — comando que o Founder roda é testado **como ele roda**, dentro do contêiner (📊 `ModuleNotFoundError: portal_worker` no console do EasyPanel em 20/09); **(c) A RESPOSTA FINAL É O RELATÓRIO DO FOUNDER** (CLAUDE.md §12.2); **(d) AGENTE ATUALIZADOR DE DOCUMENTOS** no fecho de toda SPEC (ESTADO, PENDENCIAS, DECISIONS, `TAREFAS-DO-FOUNDER.md`, painel único); **(e) o produto é MULTI-CORRETORA** — nenhum nome de corretora como constante em código, teste, script ou documento de operação; prova sempre com **2 tenants**. ⚠️ Rótulos "v11", "v11.2", "opção B", "laço curto", "3 juízes", "AAA FAST sequencial" são **históricos**, nunca rito | v13 como único **93** × manter "em teste" **60** (o rito já foi medido em 2 SPECs; duplicidade de rito é o que confunde) × voltar ao v12 sequencial **35** (📊 3× o custo e 2× o relógio) | `PROTOCOLO-AUTOBROKERS-AAA.md` v13 · `CLAUDE.md` §2/§9/§12.2 · `docs/canon/pacotes/` |
| 🧑 **D-E0017-03** (FECHADA 20/09) | **Os cortes do veredito do piloto valem como propostos** na `SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md` § P4 | cortes escritos **85** × sem cortes, veredito por impressão **40** | régua do piloto |
| 🧑 **D-E0017-04** (FECHADA 20/09, opção C) | **No 4º dia um AVALIADOR** — agente do plano Claude, **nunca a API do produto** — **lê uma amostra das conversas do piloto por SELECT** e dá as 3 notas que o produto não grava: *fala como humano · sabe calar · apólice certa de primeira*. No relatório entram **só contagens**, nunca conversa. Os escritores duráveis continuam como pendência **P-E0017-03**, para o produto medir sozinho no futuro | C **88** × folha diária da atendente **60** (🧑 o Founder disse que é difícil) × SPEC de escritores antes do piloto **70** (adia o piloto e toca o atendimento na véspera) | P-E0017-03 |
| **D-FILA-01** (20/09/2026) · 🔁 **a ORDEM foi substituída pela D-MC-38 em 04/10/2026**; o item (2), toda SPEC drena as pendências que toca, continua valendo | **Não haverá uma "SPEC de pendências" agora.** A regra: **(1)** pendência ≥ 90 de **SEGURANÇA/isolamento entre corretoras** entra no escopo da **EXTRA-001.8** — inclusive as duas da lista do Founder: *"três rotas apagam/alteram conexão por id sem conferir de quem é"* e *"nome de atendente real dentro de dado global de corredor"*; **(2)** toda SPEC **drena** as pendências dos arquivos que tocar (protocolo §2); **(3)** depois da 001.0/001.9 e **ANTES** de abrir a EXTRA-002, roda-se **UMA triagem de pendências** (agente leitor, ~1 h): fecha as já resolvidas, funde duplicatas, e o que sobrar ≥ 80 vira o bloco **EXTRA-001.11 · pendências que pesam**; **(4)** o resto espera o fim da sequência principal (renovação, cotação) | esta regra **88** × SPEC de pendências agora **55** (atrasa vidros/isolamento e metade está vencida: 📊 "40 das 81 linhas erradas" já foi resolvida pela 001.5.2; "grupo da AutoFleet dentro da Resulta" e "arquivo de credenciais na árvore" foram resolvidos pelo Founder) × só no fim de tudo **45** (deixa risco de segurança aberto ao ligar a 3ª corretora) | `specs-propostas/IDEIA-BLOCO-EXTRA-001.11-PENDENCIAS-QUE-PESAM.md` |

### Decisões da SPEC-EXTRA-001.10 (21/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; rito AAA v13 · O FIO, D-PROTO-12)

| # | decisão | notas | onde |
|---|---|---|---|
| **D-E00110-01** | **Contato no portal:** solicitante declarado **Corretor ("6")** — é a verdade, quem abre é a corretora e ela recebe cópia por e-mail — com **celular e e-mail DO SEGURADO** como contato (`Tipo 20`), porque é o segurado que a loja precisa achar para agendar e é ele que o portal notifica | segurado como contato + corretor declarado **88** · tudo da corretora, como é hoje, **60** (📊 o portal marca `PossuiTelefoneRecebeWhatsapp:false` e a loja acaba ligando para a corretora) · declarar "O Próprio" **45** (declaração falsa) | SPEC §7 · D-E00110-F1 |
| **D-E00110-02** | **Reparo × troca:** a pergunta entra na COLETA ("se a seguradora oferecer reparo grátis em 30 min, você aceita tentar?") só quando a família é para-brisa; sem resposta e com oferta do portal, o robô **para ANTES** de materializar o pedido e pergunta | coletar antes **90** × decidir pelo segurado **10** × sempre troca **30** | SPEC §7 |
| **D-E00110-03** | **Seguradora por dado ao vivo:** o slug sai de `GET /seguradoras/` na hora; os apelidos são só dica. As duas listas fechadas morrem | ao vivo **92** × tabela de 38 no código **70** × os 3 slugs de hoje **5** (📊 escrevia ZERO nos 3 HAR da Yelum) | `vidros_api.py:615` |
| **D-E00110-04** | **O canário fica na caixa do Founder**, com roteiro pronto; a SPEC entrega tudo verde offline sobre 3 HAR reais. Motivo: exige Implantar + veículo/CPF de teste (CLAUDE.md §10-5) | entregar + roteiro **85** × esperar o Founder com a branch aberta **40** | relatório §8 · D-E00110-F2 |
| **D-E00110-05** | **Bradesco entra na lista por dado, mas o API-first devolve `None` para ele** (D-PILOTO-17: captura dupla antes de escrever) | **90** × tratar como as outras **55** | `resolver_seguradora` |
| **D-E00110-06** | **RIGOR ANTES DA FRONTEIRA, só IGUALDADE DEPOIS:** antes de materializar o pedido, causa, cidade (com UF escrita), perímetro (enum) e peça (identidade conferida) são exigidos literalmente contra o que o portal publicou; depois da fronteira só se compara igualdade, e o que não bate vira **parada com número**, sem promessa de continuação | rigor antes **92** × casadores tolerantes nos dois lados **35** (📊 era o que fazia a causa virar outra causa, a cidade virar homônima de outro estado e o perímetro degradar para "Não sabe") | conserto único `4e14a1f` |
| **D-E00110-07** | **`DataSinistro` viaja em ISO com o offset derivado do FUSO da corretora** (📊 `T03:00:00.000Z` em 4 de 4 capturas, no GET e no POST) | fuso derivado **94** × offset cravado no código **58** (quebra fora de Brasília) × mandar só a data **30** (o portal recusa) | `vidros_apifirst.py` · P-E00110-A10 |
| **D-E00110-08** | **Pular o aquecimento de 17 perguntas** do prompt de abertura: o protocolo v13 §8 diz que aquecimento nunca entra, e o BLOCO 0 foi refeito sobre a captura real, que é fonte melhor | pular **75** × rodar **60** (custa relógio e responde pelo que o código já dizia, não pelo portal) | relatório §4 (quebra declarada) |
| **D-E00110-09** | **Agenda e vistoria NÃO concluem o work_run, e o vigia avisa a equipe sem depender do modelo:** quando o portal abre agenda ou pede vistoria, o trabalho não acabou — o run fica aberto para a Fila enxergar e o alerta ao suporte é disparado por código | não concluir + alerta por código **90** × confiar no modelo para avisar **30** (📊 mutação "vigia calado em agenda" passava despercebida) | `vigia_do_portal.py` · P-E00110-C-03 |
| 🧑 **D-E00110-F1** (ABERTA) | **Confirmar o contato do segurado no portal.** A execução recomenda o desenho de D-E00110-01 (celular e e-mail do segurado, solicitante Corretor). Só um acionamento real prova que o portal aceita `Tipo 20` e passa a notificar o segurado | recomendado **88** · a alternativa é manter tudo da corretora, como hoje, e a loja continuar ligando para a equipe | decide o Founder, no canário |
| 🧑 **D-E00110-F2** (ABERTA) | **Quando ligar `PORTAL_VIDROS_API_FIRST` em produção.** A execução recomenda: **só depois do canário verde**, e com `PORTAL_CANARIO_ALLOWLIST` limitada ao job do ensaio | canário antes **95** × ligar junto com o Implantar **20** (abriria pedido real sem nenhuma prova ao vivo) | decide o Founder |
| 🧑 **D-E00110-F3** (**RESOLVIDA** 24/09) | **A EXTRA-001.10.1 (a continuação) entra antes da 001.8?** Recomendação 💭 da execução: **sim, 80** — sem continuação, toda parada depois do protocolo termina em mão humana, e é justamente o trabalho manual que a SPEC existe para eliminar | 001.10.1 antes **80** × 001.8 (isolamento entre corretoras) antes **70** (é segurança, e sobe de prioridade quando entrar a 3ª corretora) | decide o Founder → executou-se a 001.10.1 (este bloco) |

### Decisões da SPEC-EXTRA-001.10.1 (24/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; rito AAA v13 · O FIO, D-PROTO-12)

> A SPEC entrega a **continuação** de um atendimento já aberto (token do portal guardado cifrado) e o **agendamento
> concluído**, atrás de `PORTAL_VIDROS_API_FIRST`, que continua DESLIGADA. D-E00110-F1 **RESOLVIDA** (o Founder já
> tinha decidido o contato do segurado, D-E001101-04 abaixo confirma o desenho) · D-E00110-F3 **CUMPRIDA** (a linha
> acima).

| # | decisão | notas | onde |
|---|---|---|---|
| **D-E001101-01** | **Onde mora o token:** cifrado pelo cofre do portal-worker (`PORTAL_VAULT_KEY`) dentro de `portal_jobs.evidence["continuacao"]`, com o instante de emissão; nunca em claro | cofre **88** · Redis com TTL 60 (`REDIS_URL` nunca confirmado no worker) · coluna nova + migration **70** · manter o job vivo esperando **40** | relatório §1 B0.13 |
| **D-E001101-02** | **Agendamento:** preferência (a partir de que dia · manhã/tarde) coletada ANTES; o robô agenda na mesma sessão a loja mais próxima e o 1º horário que casa, e confirma lendo o portal; sem casamento, apresenta as opções e continua quando o segurado escolher | preferência + continuação **90** · só continuação **70** (depende do token viver até a resposta) · equipe agenda na mão (hoje) **20** | SPEC §7 |
| **D-E001101-03** | **E-mail do corretor:** Perfil de Acionamento → e-mail do contato principal da corretora → nenhum (`EmailCorretor` nulo) | regra do banco **90** × e-mail fixo de atendente **10** (CLAUDE.md §13.9) | `portal_tool._load_profile` |
| **D-E001101-04** | **Contato (fecha D-E00110-F1, respondida pelo Founder):** Corretor (6) como solicitante declarado + celular e e-mail do SEGURADO como contato (`Tipo 20`) + WhatsApp marcado | **88** (escolha do Founder) | relatório §8 |
| **D-E001101-05** | **Domicílio:** fora; o robô não pergunta e não oferece | decisão do Founder | P-E00110-C-01 (MORREU) |
| **D-E001101-06** | **`BloqueadoIlhaNormal` deixa de travar o roteador** — o portal não lê essa chave (0 ocorrências em 3 bundles) e segue para o modal de prioridade + vistoria; a fraude (`BloqueadoPorFraude`) **continua travando** | seguir o portal **90** × manter a trava geral **40** | relatório §1.1 (perícia do bundle) |
| **D-E001101-07** | **Peça reescrita pelo agente:** se há um pedido irmão (mesmo `company_id`) esperando resposta, a peça reescrita **vira continuação** dele, nunca um 2º `abrir_atendimento`; sem pedido irmão esperando resposta, peça nova é pedido novo | continuação do irmão **85** × sempre pedido novo **60** (📊 era o defeito EXCLUSIVO do red team que atravessou da 001.10) | relatório §4, achados 8 e 11 |

**Pendências novas desta SPEC:** `P-E001101-01…17` (em `PENDENCIAS.md`).

### Decisões da SPEC-EXTRA-001.8 (21/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; rito AAA v13.1)

| # | decisão | notas | onde |
|---|---|---|---|
| **D-PROTO-13** (21/09) | **O protocolo passa à v13.1** (commit `2f03c67`): as **5 lições da EXTRA-001.10** viram regra, junto do teto de 24 agentes (D-PROTO-11) e do relatório CRÍTICO ≤ 25 KB. As cinco: **(a)** o pacote de todo subagente carrega §0–§3, §5 e §7.3 — 📊 o contexto do gerente chegou a 410 k quando o pacote foi montado à mão; **(b)** fatia grande vira fatias — 📊 um builder chegou a 788 k e respondeu por 65 % do custo da SPEC; **(c)** a **costura** é entrega, não sobra — 📊 7 quebras reais entre o que um lado monta e o outro lê, invisíveis aos gates de unidade; **(d)** ⛔ script de juiz **nunca** toca o banco real (📊 um tocou, com `company_id` falso, e só não estragou porque o banco recusou); **(e)** 🔴 a tabela de achados do relatório é **reconferida contra os laudos completos** antes de ser escrita — 📊 na 001.10 ela saiu com autoria errada e um exemplo que ninguém mediu, e o guarda automático passou verde porque confere forma, não verdade. 📊 Depois da mudança: protocolo 21,94 KB, núcleo 10,95 KB, guarda 78 ok / 0 falhas | v13.1 **90** × manter o v13 puro **55** (as cinco lições foram compradas com defeito material) × reescrever o protocolo inteiro **30** | `PROTOCOLO-AUTOBROKERS-AAA.md` · `PROTOCOLO-AAA-EVIDENCIAS.md` |
| **D-E0018-01** | **O estado de admissão (cota, teto global, chaves em espera) vive no nível do MÓDULO**, não da chamada. 📊 Motivo medido no BLOCO 0: `check_buffers` roda a cada 1 s com `max_instances=10` e **cada varredura criava o seu próprio `Semaphore(6)`** — o "teto de 6" real chegava a 60, e uma cota local viraria 40 | módulo **92** × local à chamada **(furo medido)** | relatório §1 B0.8 |
| **D-E0018-02** | **A cota é NÃO-BLOQUEANTE:** quem não tem vaga é **adiado**, e o `adiar` só faz `EXPIRE` (nunca toca o debounce). O **teto global** continua bloqueante | cota não-bloqueante **92** × semáforo por corretora **48** · teto global bloqueante **90** | SPEC §6.3 |
| **D-E0018-03** | **Teto por chamada ao modelo = 90 s.** ⚠️ A regra "p95 × 3" da proposta **não se aplica**: 📊 o p95 medido (107 s) é de **TURNO**, não de chamada — aplicá-la daria 321 s, três vezes o turno inteiro | 90 s **85** × "p95×3" = 321 s **40** | SPEC §7.1 |
| **D-E0018-04** | **Teto por turno = 300 s** (a construção tinha posto 180 s). Motivo: 90 s × 3 tentativas = 270 s **tem de caber** — com 180 s o corte vinha antes do erro final do SDK e o disjuntor nunca abria | 180 s na construção **82** × 120 s da proposta **55**; 300 s no conserto **85** × baixar a chamada para 60 s **60** | SPEC §7.2 |
| **D-E0018-05** | **O timeout de turno NÃO devolve a rajada ao buffer:** depois do `get_and_clear` não há como saber se o envio saiu | não devolver **88** × devolver **45** (risco de resposta duplicada ao segurado) | SPEC §7.2 |
| **D-E0018-06** | **Chave `sem-integracao` é adiada SEM renovar a vida:** ela já não era respondida (a trava da 001.2 a recusa), e renovar a vida de quem ninguém vai atender é guardar lixo para sempre | **90** | SPEC §6.4 |
| **D-E0018-07** | **Dois defaults de paralelismo:** 6 no caminho legado/dublê e 24 no caminho com cota (o de produção), para **não editar** o guarda herdado `test_midia_e_concorrencia_do_webhook.py:519` | dois defaults **85** × editar o guarda **70** | SPEC §6.2 |
| **D-E0018-08** | **Nenhum 2º laço de retry, e 401 NUNCA abre o disjuntor.** 📊 Os SDKs já não repetem 400/401/403/404 (`openai/_base_client.py:821-862`, `anthropic/_base_client.py:842-874`). O 401 fica fora do disjuntor porque a chave de API hoje é **GLOBAL**: no dia em que for por corretora, um 401 de uma fecharia o provedor para todas | escrito ao lado da regra | SPEC §7.3 |
| **D-E0018-09** | **O disjuntor é alimentado por callback na fábrica, e o processador pergunta a ele ANTES de consumir o buffer** — um disjuntor que ninguém consulta antes do `get_and_clear` não retém nada | **92** | SPEC §7.4 |
| **D-E0018-10** | **Não mexer no `graph.py`** (o relógio de silêncio do SSE): o timeout do httpx é por leitura entre pedaços, e um turno que emite delta não está travado. Entrou um guarda que **proíbe** `wait_for` total em volta do `astream_events` | não mexer **85** × mexer **62** | SPEC §7.2 |
| **D-E0018-11** | **Cerca do MCP dentro do serviço:** confirmar o agente da corretora e agir com `id` + `agent_id`; e **404 em vez de 403** para id alheio (403 confirma existência) | dentro do serviço **92** × coluna `company_id` nova **41** × só RLS **35**; 404 **84** × 403 **78** | SPEC §9.5 · P-098 |
| **D-E0018-12** | **A varredura do buffer fica FORA do lock de líder** (ela não envia por conta própria, e parar de varrer é pior que varrer duas vezes); **perder a liderança usa `pause_job`/`resume_job`** — 📊 no APScheduler 3.11.3 `start()` depois de `shutdown()` levanta `SchedulerAlreadyRunningError`; e o **poço de threads** passa a ter piso `max(32, cpu+4)` | varredura fora **92** × dentro **38** · pause/resume **93** × shutdown+start **22** · poço **91** | SPEC §9 |
| **D-E0018-13** | **Costura do disjuntor, opção (ii):** *"algum provedor barrado? só então resolve escopo→provedor, com cache de 60 s"* — varredura sem provedor barrado não paga nada | **90** | SPEC §7.4 |
| **D-E0018-14** | **O turno do atendimento fala o vocabulário do chat:** UPDATE por `id` + `conversation_id` **depois** do envio; `stages` com o mesmo nome **e mesmo tipo** (lista de texto) e uma chave **nova** `stage_ms` para os tempos; e **`expiradas_acumuladas`** em vez de `expiradas_24h`, porque um `HINCRBY` com TTL renovado **não é** janela deslizante | UPDATE **92** · `stages`+`stage_ms` **88** · `expiradas_acumuladas` **92** | SPEC §5.1 e §10 |
| **D-E0018-15** | **`fila_cota_ms` conta desde o 1º adiamento por cota**, não desde a última tentativa | **88** × "última tentativa" **62** | SPEC §5.1 |
| **D-E0018-16** | **`max_instances` = teto global + folga (24 + 16 = 40).** 📊 O teto real era **10**: com 10 turnos em voo o APScheduler pulava as varreduras seguintes e ninguém renovava o TTL de quem esperava. Redesenhar a varredura para não esperar os turnos é o desenho certo para escala, e grande demais para um conserto → pendência com gatilho (P-E0018-06) | 40 **82** × redesenhar agora **75** | SPEC §9.4 |
| 🧑 **D-E0018-F1** (PROPOSTA, decide o Founder) | **Aceitar o X do G3 e o teto de turno de 300 s como os PRIMEIROS ALVOS DE LATÊNCIA declarados do projeto.** 📊 Até 21/09/2026 o projeto não tinha SLO nenhum escrito. O que se propõe: *"o p95 de uma corretora sadia com a vizinha travada não passa do p95 dela sozinha mais X, com X = max(0,120 s; p95 sozinha × 0,25)"*, e *"nenhum turno de atendimento passa de 300 s"*. ⚠️ Registrado como **proposta**, não como decidido: a execução escolheu os números para poder gatear, e transformá-los em compromisso do produto é decisão do Founder | declarar os dois como alvo **💭 85** × seguir sem alvo escrito **40** ("nenhuma interferência" volta a não ser verificável) | relatório §0.0 · SPEC §5.4 |

### Decisões da SPEC-EXTRA-002 · parte 1 (22/09/2026 — ⏳ PROPOSTAS AGUARDANDO O FOUNDER; modo investigação, nada foi executado com base nelas)

> 🔁 **04/10/2026 (programa multicálculo):** D-E002-01 **substituída pela D-MC-23** · D-E002-02 **confirmada pela D-MC-24** · D-E002-04 revista pela D-MC-32 (proposta) · D-E002-07 **substituída pela D-MC-38**. As demais seguem como insumo das SPECs 129-B a 131.

> ⚠️ Nenhuma das oito abaixo está decidida. A investigação recomenda uma opção e dá nota a cada alternativa; a parte 2 da EXTRA-002 e a EXTRA-003 partem da recomendação **só depois** da confirmação do Founder. Fonte: `specs-propostas/SPEC-EXTRA-002-investigacao-prova-agger.md` §10 · relatório `reports/SPEC-EXTRA-002-INVESTIGATION-REPORT.md`.

| # | decisão | notas | onde |
|---|---|---|---|
| 🧑 **D-E002-01** (22/09, proposta) | **O caminho de integração com o Agger/Aggilizador.** 📊 A tela é uma API JSON (perícia de 3 HARs). Recomendado: **pedir C e B na mesma conversa com a Agger** — a engenharia é a mesma porta. 🔴 **Sem anuência, nenhuma automação** (nem por navegador) | **C** API oficial / acordo de integração **92** (se existir) · **B** endpoints da própria tela, com anuência escrita e usuário robô **84** · **A** navegador preenchendo a tela como uma pessoa **58** · **D** cotar direto nos portais das seguradoras **25** | proposta 002 §10 · §6 |
| 🧑 **D-E002-02** (22/09, proposta) | **Quem o robô é no Aggilizador.** 📊 Sessão única por usuário (`derrubaSessao`): o robô com o login de uma pessoa a derrubaria. Recomendado: **usuário robô dedicado por corretora** | usuário robô dedicado **95** · login de uma pessoa, só de madrugada **35** (derruba a sessão dela; auditoria misturada) | proposta 002 §10 |
| 🧑 **D-E002-03** (22/09, proposta) | **Quando calcular.** 📊 A cotação vale 5 dias (PDF-modelo e cálculo do intake). Recomendado: **apresentar em D-30 (estimativa) + recalcular em D-5 ou quando o cliente aceitar**; o D-30/D-5 é **configuração por corretora**, não constante | D-30 + recálculo **88** · um cálculo só em D-15 **68** · um cálculo só em D-30 **40** (vence antes do fechamento) | proposta 002 §10 · 003 |
| 🧑 **D-E002-04** (22/09, proposta) | **Quem envia ao cliente.** Recomendado na v1: **o AutoBrokers prepara; o corretor revisa e envia** | **A** prepara + corretor envia **92** · **C** casos simples automáticos, exceções humanas **70** (só depois de 60 dias de A medidos) · **B** envio automático por política **35** (o Approval hoje não funciona — laudo F1a §7) | proposta 002 §10 |
| 🧑 **D-E002-05** (22/09, proposta) | **"A melhor proposta".** Recomendado: **rótulos transparentes** — menor preço · mais parecida com a atual · maior cobertura · menor franquia · destaque da corretora (escolhido por gente) | rótulos transparentes **94** · uma "recomendação" escolhida por IA **30** (decisão comercial opaca) | proposta 002 §10 · 003 |
| 🧑 **D-E002-06** (22/09, proposta) | **Como a 003 se divide** (CLAUDE.md §9: nenhuma SPEC em duas sessões; 💭 14–22 h não cabem num chat). Recomendado: **003-A "a fundação"** (espera durável + `QuoteProvider` + adaptador + conexão) → **003-B "o ciclo de renovação"**, um chat cada. Nenhuma fatia é "herdada" pela 004. Nome e número finais: do Founder | 003-A/003-B **88** · proposta própria com outro número para a fundação **74** · uma 003 só, num chat **70** | proposta 002 §8/§10 · 003 |
| 🧑 **D-E002-07** (22/09, proposta) | **A posição na fila** (📊 fila vigente: 001.9 → 001.0 → triagem → EXTRA-002 → 099 → EXTRA-003). Recomendado: **parte 2 da 002 assim que a caixa do Founder estiver feita; 003 logo depois da triagem**. 💭 A diferença é pequena porque o peso da 099 não foi medido — por isso vai ao Founder | parte 2 + 003 logo depois da triagem **78** · manter a 099 (canais) antes da 003 **65** | proposta 002 §10 |
| 🧑 **D-E002-08** (22/09, proposta) | **Reclassificar a D-PILOTO-16:** o Agger/Aggilizador é **multicálculo**, não gestão — entra como porta **nova e irmã**, **`QuoteProvider`**, não como adaptador de gestão da SPEC-101. Um eventual produto de gestão da Agger continua cabendo na 101 | reclassificar como `QuoteProvider` **90** · manter a D-PILOTO-16 como está **40** | proposta 002 §0/§10 · D-PILOTO-16 |

### Decisões da SPEC-116 · Model Router + Bancada E2E (23/09/2026, tomadas pela execução com nota 0–100 — regra do Founder de 13/09; rito AAA v13)

> Texto completo e evidência: `specs/SPEC-116-cada-trabalho-no-modelo-que-provou-servir.md` §10 · relatório `reports/SPEC-116-EXECUTION-REPORT.md`.

| # | decisão | notas | onde |
|---|---|---|---|
| **D-116-01** | nome canônico **Model Router** (SPEC-052 §14), não "Model Fabric" (colide com Intelligence Fabric) | Router **95** · Fabric 40 | SPEC §0 |
| **D-116-02** | catálogo = **`llm_pricing` expandido** + snapshot gerado do banco | expandir **88** · catálogo em código 74 · YAML 70 · tabela nova 30 | migration `_01` |
| **D-116-03** | rotas por PAPEL no banco (`llm_papeis` + histórico); o código pede papel | banco **88** · env por serviço 50 · no código 45 | migration `_01` |
| **D-116-04** | a bancada **estende a Eval Fabric** da SPEC-062 (nada de `bench_*`) | estender **95** · `bench_*` 10 | migration `_03` |
| **D-116-05** | ordem **arnês → baseline → candidatos → mapa** | **92** · bancada antes do arnês 45 · trocar e medir depois 20 | SPEC §5 |
| **D-116-06** | em produção: **OpenAI + Anthropic**; Google depois de chave local + tier pago; xAI/MiMo/DeepSeek/Z.ai só laboratório, PII bloqueada | **90** · liberar por benchmark 25 | SPEC §11 |
| **D-116-07** | reserva declarada na rota, **só antes da 1ª tool com efeito**; depois retém | **85** · `with_fallbacks` 68 · sem reserva 70 | F2 |
| **D-116-08** | SDK por necessidade; checkpoint 4 condicionado à medição (📊 40/40 checkpoints reais abriram) | **86** · subir tudo 40 · nada 55 | SPEC §8 |
| **D-116-09** | bancada ao vivo com **teto de US$ 100** no código; teto de qualidade só no subconjunto crítico | **85** · sem teto 50 · US$ 20 45 | F5a |
| **D-116-10** | classes de dado `publico · interno · pii`; Fable/Mythos sem `pii` | **88** · sem classe 30 | migration `_01` |
| **D-116-11** | ciclo em dois passos: legado vira **DEPRECATED** já, **BLOCKED** só depois que a bancada provar o substituto | **90** · bloquear já 40 | migration `_01` |
| **D-116-12** | embeddings `text-embedding-3-small` **KEEP** (sem sucessor; troca = reindexar + eval de retrieval) | **85** · gemini-embedding-2 agora 35 | SPEC §10 |
| **D-116-13** | transcrição: bancada PT-BR `gpt-transcribe` × `whisper-1` antes de 26/02/2027 | **80** | P-S116-06 |
| 🧑 **D-116-14** | modelos do DESENVOLVIMENTO (protocolo §10): **não mexo no protocolo**; dívida para o Founder | **90** | P-S116-19 |
| **D-116-15** | `memory_settings.memory_llm_model` vira **legado ignorado**; a rota `memoria` manda; a migration `_02` não existe | rota manda **90** · migration de dado já 35 | F3a |
| **D-116-16** | F5a começou **em paralelo** à F1 (arquivos disjuntos, contrato declarado no pacote) | **85** · esperar a F1 60 | card |
| **D-116-17** | precedência: **a rota do papel vence o modelo gravado no agente**; o agente só manda em papel sem rota | rota vence **90** · agente vence 40 | F4 |
| 🧑 **D-116-18** | **empate em papel P0 na Onda A → o modelo de MAIOR margem**; o mais barato empatado vira desafiante da Onda B. Aplicado: portal → gpt-6-sol medium (📊 43/43; Luna 45/45) e visão → gpt-6-sol low (📊 30/30 = Luna); memória segue a régua de custo (gpt-6-luna low, 📊 39/45 × 32/45). Diferença de custo é decisão comercial (CLAUDE.md §10-2): **o Founder pode confirmar ou trocar por uma linha** | Sol no P0 **88** · Luna pela régua literal 80 · manter gpt-4o 20 | migration `_04` · `8909de2` |

**🔴 Lição registrada — o incidente do pooler (23/09/2026, resolvido).** 📊 Um script de medição desta execução deixou uma
conexão do pooler Supabase (porta 6543, modo transação) com `default_transaction_read_only=on`; o pooler a entregava a
quem conectava (12/12 sondas só-leitura). Encerrada por `pg_terminate_backend` ≈ 20:00Z; 20/20 sondas limpas depois;
impacto medido zero (nenhum turno de agente nas 10 h; o espelho grava por REST). **Regra:** script de medição **nunca**
usa `SET` de sessão pelo pooler — só `SET TRANSACTION` ou `SET LOCAL`, dentro da transação.

### Decisões da SPEC-117 · o atendimento nunca perde a apólice que encontrou (26/09/2026; rito AAA v13.2)

> Texto completo e evidência: `specs/SPEC-117-o-atendimento-nunca-perde-a-apolice-que-encontrou.md` §10 · relatório
> `reports/SPEC-117-EXECUTION-REPORT.md` · `PROTOCOLO-AAA-EVIDENCIAS.md`.
>
> 🔴 **Colisão de número, RESOLVIDA em 26/09/2026:** o identificador **D-PROTO-13** já pertencia à decisão de
> 21/09 (protocolo v13.1, EXTRA-001.8) e foi usado por engano para a decisão de 26/09. **Um número, uma
> decisão:** a decisão de 26/09 (gerente/juiz/red team → Opus 5.5) passa a ser **D-PROTO-14**, e o protocolo,
> o `PROTOCOLO-AAA-EVIDENCIAS.md`, o relatório e a SPEC-117 foram corrigidos no mesmo commit
> (📊 `grep -rc "D-PROTO-13" docs/canon/ | grep -v ':0'` → só a entrada de 21/09 e este parágrafo).
> ⚠️ A decisão de 21/09 **não** foi renumerada: ela é a mais antiga e já é citada por relatórios fechados.

| # | decisão | notas | onde |
|---|---|---|---|
| 🧑 **D-PROTO-14** (26/09) | **O gerente, o juiz e o red team passam de Fable 5.1 a Opus 5.5** — determinado pelo Founder, por escrito, na abertura da SPEC-117, junto do modelo dos builders. O protocolo foi atualizado para **v13.2** (📊 `grep -c "Fable" docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` → era **7**, ficou **0**; §3.1, §4, §8 e §10). ⛔ **Nenhum gate reduzido:** juiz e red team seguem **frescos, paralelos e cegos um ao outro**, a confirmação curta segue obrigatória depois de blocker, a trava de duas rodadas segue contada por `backend/scripts/rodada_do_juiz.py` e a mutação dos guardas novos segue no passo ③. ⚠️ **O limite honesto:** é **decisão, não medição** — nenhum número diz que Opus 5.5 julga melhor que Fable 5.1, a comparação não foi feita; se o julgamento piorar em duas SPECs, volta-se ao número anterior (regra §13 do protocolo) | decisão expressa do Founder, sem contrária registrada | `PROTOCOLO-AUTOBROKERS-AAA.md` §3.1/§4/§8/§10 · `PROTOCOLO-AAA-EVIDENCIAS.md` (entrada D-PROTO-14 de 26/09) |
| 🧑 **D-S117-01** (era a D4 da proposta) | **Só o conserto completo — sem hotfix de uma linha antes.** Decisão expressa do Founder na abertura da SPEC | conserto completo **(escolha expressa do Founder)** × hotfix de 1 linha antes **descartado** | SPEC §10 D4 |
| **D-S117-02** (era a D7) | **A máscara de identidade FICA, e o conserto é na porta.** Razão: o dado mascarado **já** traz número, seguradora, ramo, vigência, situação e o código interno do cliente; o que falta é só a identidade — e para responder *"é o mesmo cliente"* basta um **pseudônimo opaco**. Dar CPF em claro ao agente que fala com o segurado reabriria risco de LGPD **sem necessidade** | manter e consertar a porta **95** × identidade crua no atendimento **25** × papel novo **15** | SPEC §2 e §10 D7 |
| **D-S117-03** (era a D3) | **O pseudônimo do cliente (`cliente_ref`) é HMAC com o `company_id` DENTRO do material, e a chave vem do ambiente** — o isolamento por corretora não depende de uma chave por corretora, e o G9 o prova (📊 mesmo `codfil:codigo` em duas corretoras → `cliente_ref` diferente). A escolha da variável dedicada ficou como pendência **P-S117-08** | HMAC com chave de plataforma + `company_id` no material **85** × HMAC com chave por tenant no Vault **70** (exige chave nova por corretora; não há porta pronta hoje) × `sha256` sem chave **25** | SPEC §10 D3 · P-S117-08 |

### Decisões da SPEC-118 · o formulário dentro do WhatsApp funciona, e o agente sabe o que vem (26/09/2026; rito AAA v13.2)

> Texto completo e evidência: `specs-propostas/SPEC-118-o-formulario-dentro-do-whatsapp-funciona-e-o-agente-sabe-o-que-vem.md` ·
> relatório `reports/SPEC-118-EXECUTION-REPORT.md`. Notas 0–100 pela regra do Founder de 13/09
> (*"não pare para perguntar; dê nota às opções, escolha a melhor e me avise no relatório"*).

| # | decisão | notas | onde |
|---|---|---|---|
| 🧑 **D-118-01** | **A finalização fica em `test` com lista explícita enquanto os testes correm, e vai a `live` depois do formulário provado — com a lista apagada.** O Founder pediu *"todas as seguradoras liberadas, para não ter confusão depois"*. 🔴 **O que evita a confusão não é liberar tudo: é a trava.** Hoje um `ref` escrito errado em `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` **nunca finaliza, em silêncio** — e uma lista seletiva permanente é justamente a configuração que "esquece" o corredor novo. 📊 Estado conferido no `/health` em 26/09: `finalize_abre_de_verdade: ['porto-auto-whatsapp@v1','yelum-auto-whatsapp@v3']`, os dois resolvendo. ✅ **A trava que torna o `ref` fantasma visível foi FEITA nesta SPEC** (`/health` publica `finalize_refs_fantasma`; guarda com 4 linhas de controle, uma delas provando que o aviso sobrevive ao modo `live`) — **P-118-15** fechada | `test` + lista durante os testes, `live` depois **88** × `live` já agora **55** (abre 14 seguradoras antes de o formulário estar provado) × lista seletiva para sempre **40** | SPEC-118 §5 · P-118-15 |
| **D-118-02** | **O conserto de `_STREET_RE` (a abreviação `R.`) entra NESTA SPEC, e só nela, porque só ela tem a régua.** Mexer no reconhecedor de logradouro move `local_rua`/`destino_rua` nas 73 rotas; o controle exigido foi a **régua completa antes e depois**, com a regra de que **nenhuma rota pode cair** — e, se caísse, reverter em vez de forçar o número | consertar com régua antes/depois **90** × adiar para a próxima SPEC **60** (o defeito chega ao segurado enquanto isso) × consertar sem medir **10** | CHANGE-ADDENDA 26/09 · §A do relatório |
| **D-118-03** | **O corpus da régua NÃO é regerado nesta SPEC.** 📊 Existe `gerar_corpus_de_telas.py --todas` e o modo seco rodou verde em 26/09, trazendo ~51 sessões novas. Regerar **muda a nota das 73 rotas** — no mesmo commit em que um conserto de produto também as move. Misturar os dois tira o direito à conclusão (CLAUDE.md §9.2: sem linha de controle, o acerto se credita ao lugar errado) | adiar com pendência escrita **85** × regerar junto **35** × regerar e não medir **5** | P-118-08 · P-PILOTO-06 |
| **D-118-04** | **A aba CORREDORES publica os números de hoje E declara que eles não são comparáveis aos de 24/08.** O denominador da régua saiu de 106 para 76/70/64 desde a SPEC-089. Esconder a diferença faria a página parecer uma piora do produto; omitir os números de hoje manteria a página mentindo há um mês | publicar + declarar a não-comparabilidade **92** × manter a foto de 24/08 com aviso **40** × publicar sem a ressalva **20** | painel, aba CORREDORES |
| **D-118-05** | **A restauração das mutações da régua ganha rede de segurança nesta SPEC.** 📊 26/09 20:37 a régua morreu em `OSError: [WinError 1224]` dentro do `finally` que restaura, e deixou um arquivo de **produção** mutado na árvore. Não é mudança de produto — nenhum eixo, corredor ou nota depende dela — e é o agravamento medido de **P-E0013-09**, cujo preço esta SPEC já pagou uma vez (commit `d910613`) | consertar a restauração **88** × só declarar **55** (a próxima rodada repete o estrago) × rodar a régua em cópia da árvore **70** (resolve, mas é obra maior) | CHANGE-ADDENDA 26/09 · P-118-14 |

### Decisões da SPEC-119 · os corredores ficam prontos para a vida real (28/09/2026; rito AAA v13)

> Fatia **F5 — a página deixa de confundir**. Notas 0–100 pela regra do Founder de 13/09
> (*"não pare para perguntar; dê nota às opções, escolha a melhor e me avise no relatório"*).

| # | decisão | notas | onde |
|---|---|---|---|
| **D-119-01** | **A demanda passa a ser um retrato VERSIONADO E DATADO, lido sem banco.** A régua mede offline (o corpus está em git) e `observed_events` exige credencial. Se a coluna dependesse do banco, ela voltaria a imprimir `0` quando ele faltasse — que é o defeito que esta fatia existe para matar. O retrato grava `medido_em`, `fonte`, `comando` e o **controle** (`marcas_de_corretora`, 📊 8 em 28/09) dentro do próprio arquivo, e a régua imprime `—` quando ele não existe | retrato versionado + datado **90** × a régua consulta o banco toda vez **45** (offline volta a dar `0`, e a rodada fica 10× mais cara) × número digitado na página **10** (não carrega data — é o defeito de hoje) | `demanda_por_rota.py` · `reports/DEMANDA-POR-ROTA.json` |
| **D-119-02** | **`DEMANDA_MEDIDA` é RENOMEADA, não comentada.** O nome afirmava ser a demanda medida e guardava o total de um serviço em todas as seguradoras, em 21/08. Um comentário ao lado não protege o próximo leitor — 📊 já havia um comentário com a data, e ele não impediu que o `72` chegasse ao Founder como "os pedidos da Mapfre" | renomear para `DEMANDA_GLOBAL_POR_SERVICO_21_08_2026` **88** × apagar a constante **45** (a lista de coleta precisa do ranking e teria de ser reescrita) × só comentar **30** (CLAUDE.md §12.1 chama isto de consertar o sintoma) | `padroes_de_servico.py` · `lista_de_coleta.py` |
| **D-119-03** | **A aba CORREDORES passa a ser GERADA por programa, e o gerador RECUSA gravar quando acha defeito.** 📊 A aba de 26/09 carimbava "medido em 26/09" no topo **e** trazia `mapfre/auto/guincho · 72 pedidos` no corpo, um número de 21/08 sem rótulo nenhum. **O carimbo do topo não protege o número de baixo** — só um gerador protege, porque nele nenhum número é digitado | gerar a aba, com guarda que recusa gravar **92** × reescrever à mão com cuidado **50** (é o que se fez em 26/09, e o `72` passou) × publicar com ressalva **25** | `pagina_dos_corredores.py` · aba CORREDORES |
| **D-119-04** | **Três retratos, três datas, e elas aparecem SEPARADAS na página.** A demanda vem do banco (vivo, 28/09); a nota e o "dá para ligar" vêm do corpus versionado no commit. Unificar numa data só seria mais bonito e seria mentira — 📊 `allianz/auto/guincho` tem **29** sessões no banco e **10** no corpus, e a diferença é a cota da geração, não erro | publicar as três datas **90** × uma data só, a mais antiga **40** (esconde que a demanda é mais nova) × uma data só, a mais nova **15** (data emprestada = a "informação antiga sem rótulo" de novo) | aba CORREDORES · `CORREDORES-POR-ROTA.md` |
| **D-119-05** | **G1 e G2 ficam DECLARADOS COMO NÃO CUMPRIDOS, com a evidência, em vez de afrouxados.** 📊 `mapfre/auto/guincho` não tem uma conversa **nem no corpus nem no banco** — o gate exige um acionamento real, que é trabalho de pessoa. ⛔ Nenhum gate foi reduzido e nenhum escopo foi cortado (CLAUDE.md §11/D5): os dois viraram **P-119-01** e **P-119-02**, com o que destrava escrito | declarar não cumprido + pendência **95** × reescrever o gate para caber no que foi feito **0** (é afrouxar a régua, proibido pelo protocolo §5) × bloquear a SPEC **30** (a fatia entrega valor sem eles, e o que falta não é código) | P-119-01 · P-119-02 |
| **D-119-06** | **O UUID de corretora em `regua_motor.py:287` NÃO é consertado nesta fatia.** É defeito real de §13.9 e é pré-existente. Mas ele alimenta a exclusão do Espelho, que alimenta o item de apelidos do eixo D — mexer nele move a nota das 73 rotas **no meio da medição que prova o G4**, e a comparação antes/depois deixaria de ter direito à conclusão (CLAUDE.md §9.2) | pendência com o que custa esquecer **85** × consertar agora **55** (invalida o G4 desta SPEC e exige re-rodar 18 min) × ignorar **0** | P-119-06 |
| **D-120-A** | **A Bradesco pergunta "precisa de polícia?" só quando a pane é de uma lista FECHADA.** A tela pergunta se há ocorrência policial; responder "Não" num roubo mente para a seguradora, responder "Sim" numa pane de bateria trava o caso. `policia_pela_pane` responde "Não" só para panes mecânicas nomeadas; o resto vai à pergunta ao segurado | lista fechada de panes **88** × sempre "Não" **30** (mente num sinistro) × sempre perguntar **60** (uma pergunta a mais em 📊 todas as sessões medidas) | `corridor_playbooks.py` |
| **D-120-B** | 🧑 **ABERTA — a Porto avisa o preço da bateria e pergunta "Posso continuar o agendamento?"; hoje o agente responde "Sim".** 📊 Pelo passo `agendamento_seguir_porto`, que já respondia assim na base `0c0e070` — não é regressão desta SPEC. Continuar é aceitar o custo de uma bateria nova em nome do segurado | perguntar ao segurado antes de continuar **85** × manter o "Sim" **40** (aceita custo sem ele saber) × mandar a uma pessoa **55** (trava um caso que ele resolve com uma palavra) | P-120-17 |
| **D-120-C** | 🧑 **ABERTA — a tela de amperes COM PREÇO vai a uma pessoa**, contra a regra "nunca humano nos amperes". Escolher uma opção com preço é aceitar custo (regra da SPEC-119). 📊 Nenhuma tela assim no acervo: é defesa | manter com pessoa até existir uma tela real **80** × perguntar ao segurado com o preço **70** × escolher pela tabela de porte **20** (aceita custo) | P-120-18 |
| **D-120-D** | **A Porto que pergunta "manter o horário?" recebe "Sim".** 📊 Nas conversas gravadas, a atendente humana respondeu Sim em todas; o horário é o que o segurado já pediu | "Sim" **86** × perguntar **55** | `corridor_playbooks.py` |
| **D-120-E** | **"Continuar de onde parou?" recebe "Continuar".** Recomeçar faz o segurado repetir tudo. ⚠️ A justificativa escrita promete uma conferência do resumo que na Yelum chega depois da abertura (P-120-16) | "Continuar" **80** × "Recomeçar" **45** | P-120-16 |
| **D-120-F** | **HDI residencial "deseja abrir nova solicitação?" recebe "Não" quando o caso já foi aberto nesta sessão** — abrir duas vezes gera dois técnicos | "Não" com a trava da sessão **84** × sempre "Sim" **25** | `corridor_playbooks.py` |
| **D-120-G** | **HDI tem duas identidades (D12):** no auto, o agente é "Sou corretor(a)"; no residencial, "Sou segurado(a)", como o Founder decidiu. 📊 As duas vêm do que a URA aceita em cada ramo nas conversas gravadas | por ramo **88** × uma só **40** (a residencial devolve ao menu) | `corridor_playbooks.py` |
| **D-120-H** | **O vigia ainda TENTA DE NOVO o primeiro aviso que NUNCA saiu — só por 2h.** O juiz achou que tirar o lembrete tirou também a rede de segurança (📊 grupos desativados de 10 a 21/09 = pedidos de ajuda que ninguém recebeu). A regra do Founder tem duas metades: "um aviso só, na hora" E "nunca travar sem chamar ninguém" | nova tentativa só em caso recente e com a vez livre **90** × nenhuma nova tentativa **45** (pedido perdido fica perdido) × lembrete como antes **5** (é o print de 244h) | `handoff_watchdog.py` · P-120-15 |
| **D-120-I** | **O dossiê do grupo sai SEM MÁSCARA** — WhatsApp completo e clicável, CPF/CNPJ, nome. Ordem literal do Founder: *"é um humano da corretora, não podem estar mascarados"*. O grupo é da própria corretora; a máscara continua valendo em log, teste, documento e acervo (§7, §13.9) | sem máscara no grupo **92** × mascarado **20** (a atendente não consegue ligar) | `insurer_dispatch_service.py` · `human_handoff.py` |
| **D-120-J** | **A assistência do dia é anotada quando o PROTOCOLO existe, não quando o caso fecha.** 📊 O red team mediu: o fechamento só acontece no follow-up + 2h30 — um guincho aberto às 16h sumia do resumo das 19h | na abertura (`monitoring`), uma vez por sessão **90** × no encerramento **35** | `dispatch_router.py` · `os_modelos_do_grupo.py` |
| **D-120-K** | **A lista de telas sem resposta foi LIMPA e o histórico ainda não empurrado REESCRITO.** O primeiro `TELAS-SEM-RESPOSTA-DOS-16.json` trazia a resposta crua da atendente (placa, rua, nome). Ficam as 51 opções que estão na tela; as 34 respostas livres viram `<texto livre, N caracteres — mascarado (§13.9)>` | reescrever só o que não subiu **90** × commit de correção por cima **30** (o dado cru fica no histórico da `main` para sempre) | `reports/TELAS-SEM-RESPOSTA-DOS-16.json` |
| **D-PROTO-15** | **O teto de agentes por sessão sobe de 24 para 50, e todo investigador passa a ser Opus 5.5.** Ordem do Founder em 29/09/2026, depois que o teto de 24 obrigou a SPEC-119+120 a reusar juiz e red team: *"toda hora estamos tendo problemas com esse teto"*. O limite de agentes SIMULTÂNEOS (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=2`, `.claude/settings.json`) é outra coisa e não mudou | 50 **90** × manter 24 **30** (serializa e força reuso de revisor) × sem teto **40** (o hook é o que impede "estourou, chama mais gente") | `.claude/hooks/teto-de-agentes.py` · protocolo §10 |
| **D-PROTO-16** | **Até QUATRO agentes ao mesmo tempo (era dois).** Decisão do Founder em 29/09/2026, na abertura da SPEC-121 ("subir para 4 os agentes simultâneos", nota 85 × 50). Continua valendo a regra do dono único: builders em paralelo só com ARQUIVOS DISJUNTOS listados no card (§4); juiz e red team são read-only. ⚠️ O harness lê a env ao abrir a sessão: vale a partir do chat seguinte | 4 **85** × manter 2 **50** (fatias disjuntas esperam na fila) | `.claude/settings.json` · protocolo §10 |
| **D-121-A** | 🧑 **Founder, 29/09/2026 — o grupo só ouve o que o humano NÃO conhece, e a REGRA DOS 7 DIAS.** **D5:** o ✅ de conclusão e o aviso de sinistro **calam** quando a atendente participou da conversa. **D6:** o aviso tardio do vigia só sai **com prova de que foi o AGENTE quem pediu** ajuda. **D8:** Porto bateria — o agente **avisa o preço** da bateria nova ao segurado **antes** e mantém o "Sim" da URA (fecha a **D-120-B**). **D12:** condomínio e empresarial **continuam com a atendente**. **A regra dos 7 dias, no texto dele:** *"só responder se tiver msg NOVA depois dos 7 dias; não responder msgs antigas; o que já foi atendido continua sendo de humano e sem grupo; msg nova = conversa nova; grupo só se precisar de ajuda"*. 📊 O defeito que originou: os 29 avisos ao grupo de 21/09 (`work_events` grupo.enviado, reproduzido pelo juiz em 30/09: 29 de 29 em 21/09, 28 pedidos de ajuda sem motivo gravado); depois da SPEC, o teste do fio leva os 29 a **zero** | decisão do Founder — lei da SPEC (card, "Decisões do Founder") | `o_grupo_so_o_que_importa.py` (porta A agente ligado · B prova do agente · C nenhum humano em 7 dias) · `o_fim_do_atendimento.py` · `corridor_playbooks.py` · commits `823a845` `2787ff2` `c7b210c` |
| **D-121-B** | 🧑 **Founder, 29/09/2026 — o Sonnet 5 está PROIBIDO no sistema; o Sonnet 5.5 entra no lugar.** Migration `20260929_01_spec121_sonnet_5_5.sql`: `claude-sonnet-5-5` APPROVED (US$ 2/10 por MTok, o mesmo preço), `claude-sonnet-5` BLOCKED → 5.5; 8 agentes e 1 corretora migrados. 📊 29/09 `GET /v1/models/claude-sonnet-5-5` respondeu (modelo lançado em 28/09): 1M de entrada, 128k de saída, esforço até `max`. ⚠️ Três quebras vindas do 5: `thinking` desligado → 400 (o mais baixo é `between_tools`), `tool_choice` forçado → 400, `temperature` fora do padrão → 400 — a fábrica (`llm_factory`) as trata. 📊 VERIFY do juiz em 30/09 (SET TRANSACTION READ ONLY): agentes em Sonnet 5 = 0, corretoras = 0, `token_usage_logs` com Sonnet 5 nas últimas 24 h = 0. 📊 smoke real pelo caminho do produto: 2 chamadas, US$ 0,0027 | decisão do Founder | migration `20260929_01` · `llm_factory.py` · guarda `test_o_sonnet_5_esta_proibido.py` · commit `dbacf5e` · P-121-06/07/08/09 |
| **D-121-C** | 🧑 **Founder, 29/09/2026 — o carro reserva.** **Sem número do sinistro → pessoa** (o produto não guarda número de sinistro; 📊 nas 9 sessões Yelum que tinham número, **0** veio do segurado espontaneamente — `corridor_playbooks.py`, nota do passo CR1). **Sem cartão de crédito com limite → pessoa.** **Yelum "em análise"** = o agente avisa o segurado que a seguradora **confirma em até 3 horas úteis**. **Allianz, Bradesco e HDI** (sem canal claro) → pessoa. **Porto, Zurich e Mapfre** (sem conversa real no acervo) → pessoa. **Fora de 9h–17h em dia útil → pessoa.** **Diárias** = o limite do plano, senão **15** (📊 a corretora digitou 15 em 5 de 7 pedidos reais da Yelum) — o gerente pôs as notas: limite do plano ou 15 **80** × perguntar ao segurado **45**. Tokio e Azul: o link da própria seguradora e o que levar (CNH, cartão) | decisão do Founder; diárias com nota do gerente 80 × 45 | `corridor_playbooks.antes_de_acionar` (CR1–CR9) · `insurer_dispatch_tool.py` · commits `62c9b87` `42a491d` · P-121-01/02/03/05 |
| **D-121-D** | **Gerente — o pedido do AGENTE que uma PESSOA atendeu reabre depois de 7 dias com mensagem nova; o que ninguém atendeu, não reabre, e o vigia avisa.** Juiz (P2) e red team (P7) acharam, cegos um ao outro: a conversa em que o agente pediu ajuda e a atendente atendeu ficava **muda para sempre**, mesmo com o segurado voltando no dia 30 com assunto novo. 📊 2 de 477 conversas `HUMAN_REQUESTED` estavam nesse estado (SELECT read-only, 29/09). Leitura da D3 do Founder (*"o que já foi atendido continua sendo de humano; msg nova = conversa nova"*). `Admin Intervention` fica de fora (P-121-18) | reabrir só o atendido **80** × reabrir todo pedido do agente **70** (o que ninguém atendeu voltaria ao robô sem uma pessoa ter visto) × nunca reabrir **30** (contraria "msg nova = conversa nova") | `o_fim_do_atendimento.marca_do_agente` · `gente_atendeu_depois_do_pedido` · commit `42a491d` · 🧑 o Founder pode confirmar |
| **D-121-E** | **Gerente — piso de diversidade no acervo: cada rota guarda até 2 sessões SEM desfecho, as mais diferentes.** Sem o piso, a regeração do acervo tirava a prova das telas órfãs e uma rota subia para ATENDE SOZINHO **só porque a prova saiu** (📊 `porto/auto/bateria` perdia as telas da consultora e virava ATENDE falsa — commit `e0fa1b7`) — rota falsa em ATENDE SOZINHO é o pior erro da régua | piso de 2 **80** × subir o piso para 8 **55** (mais bytes, e não garante) × aceitar a perda **30** | `scripts/gerar_corpus_de_telas.py` (`PISO_DE_DIVERSIDADE = 2`) · commit `e0fa1b7` |
| **D-121-F** | **Gerente — fogão (geladeira, micro-ondas) pedido pelo menu do ELETRICISTA fica SEM etiqueta.** As telas daquelas sessões são do caminho do eletricista (tomada, disjuntor); com a etiqueta `eletrodomesticos`, entravam na rota de eletrodoméstico como 📊 3 órfãs falsas (régua da F3, 29/09) e reprovavam o corredor certo por tela de outro caminho (CLAUDE.md §9.5, pergunta C) | sem etiqueta **65** × etiquetar `eletrodomesticos` **55** | `scripts/padroes_de_servico.py` · commit `e0fa1b7` |
| **D-121-G** | **Gerente — Porto "você tem um serviço aberto… quer falar sobre ele?": "Não" só quando o aberto é de OUTRO tipo; mesmo tipo ou ilegível → pessoa.** 📊 Sessão `193c5ad6+1`: a atendente respondeu "Sim" e a conversa virou acompanhamento do guincho aberto, sem protocolo. Responder "Não" sempre pode abrir um guincho **duplicado** (D-120-F: nunca abrir duas vezes o mesmo) | outro tipo → "Não", mesmo tipo → pessoa **82** × sempre pessoa **70** (segura, mas trava o serviço diferente) × sempre "Não" **45** (abre duplicado) | `corridor_playbooks.py` (`servico_aberto_porto_auto`, `_nao_se_o_aberto_e_outro`) · commit `4ccd063` |
| **D-121-H** | **Gerente — o teto do bloco de instruções de acionamento do agente sobe de 7.000 para 8.000 caracteres, DEPOIS de compactar as repetições.** Depois de compactar, o que passa de 7.000 é serviço NOVO (carro reserva, eletricista, chaveiro), não repetição; as perguntas que o teto antigo tinha cortado voltaram (fecha a P-120-10) | compactar e subir para 8.000 **85** × só subir o teto **60** × cortar perguntas ao segurado **30** | `insurer_dispatch_tool.py` · `test_a_atendente_sabe_conduzir_um_acionamento.py` · commit `62c9b87` |
| **D-121-I** | **Evidência — o G5 (desentupimento e eletrodomésticos da Allianz atendidos pelo robô) foi REFUTADO e está declarado, sem afrouxar o gate.** O protocolo daquelas conversas foi dado por uma **pessoa da seguradora**, não pela URA; a falsa ATENDE SOZINHO do desentupimento sumiu quando a "consulta de pedido existente" saiu do acervo (`e0fa1b7`). Só um acionamento real prova essas rotas | declarar não cumprido + pendência **95** × reescrever o gate para caber **0** | P-121-03 · card da SPEC-121 (G5) |
| **D-121-J** | **O chaveiro de auto da Yelum e da HDI pergunta a garagem e o nível da rua antes de acionar.** 📊 Na sessão real e6a07317 a Yelum manda chaveiro + guincho e abre o formulário de garagem; sem os dados, a tela ficava órfã. Completa o que a F4b começou (garagem perguntada, como a D2 da SPEC-120) | perguntar antes **85** × mandar a uma pessoa **55** | `corridor_playbooks.py` (`b0aff49`) |
| **D-122-A** | 🧑 **Founder, 30/09/2026 — o GPT-6.1 Sol sucede o Sol 6.** 📊 `GET /v1/models/gpt-6.1-sol` → 200 (criado 27/09, sem data de desligamento); preço igual ao Sol 6 (US$ 2/10 por MTok) com a entrada em cache à metade (multiplicador **0,05** no catálogo); **sem esforço `none`** (📊 HTTP 400 medido, barrado antes da rede pela porta do catálogo). Migration `20260930_01`: 6.1 APPROVED; os **7 papéis primários** do Sol 6 (atendimento, chat_principal, juiz_eval, portal_decisao, subagente, visao, visao_documento) **e a reserva do dispatch** passam ao 6.1. 📊 Smoke real pelo caminho do produto, com failover do dispatch → 6.1: US$ 0,0073, conferido no ledger | decisão do Founder — lei da SPEC | migration `20260930_01` · `modelos_snapshot.json` · `docling-service/app/config.py` · `agent_council.py` · guarda `test_o_sol_6_1_sucede_o_sol_6.py` · commit `29b0b76` · P-122-01/02/08 |
| **D-122-B** | **Gerente — troca de GERAÇÃO, não de esforço: cada papel mantém o esforço e a reserva que tinha.** 📊 8 linhas em `llm_papeis_historico` (`alterado_por='migration 20260930_01'`, SELECT do juiz 30/09): em todas `linha_anterior.esforco = linha_nova.esforco` e a reserva igual. Luna, Astra, Opus e Sonnet intactos; o **Opus 5.5 continua primário do dispatch** e reserva de atendimento, chat e portal. Mudar esforço junto misturaria duas variáveis numa troca só | mesmo esforço **90** × subir o esforço aproveitando a troca **40** (o custo sobe sem medição) × baixar para economizar **35** | migration `20260930_01` · mutação M3/M7 do guarda (vermelhas) · commit `29b0b76` |
| **D-122-C** | **Gerente — o Sol 6 fica DEPRECATED, não BLOCKED.** 📊 A OpenAI não o desligou (`shutdown_date: null`; a página de *deprecations* de 30/09 não o lista); a bancada ainda pode medi-lo como linha de base, e a produção não o usa mais (📊 0 rotas). `substituido_por = gpt-6.1-sol` | DEPRECATED **85** × BLOCKED **50** (proibiria medir a linha de base, sem ganho de segurança) | migration `20260930_01` · mutação M6 (Sol 6 de volta a APPROVED → vermelho) |
| **D-122-D** | **Gerente — a D4 da proposta REVISADA: os braços da bancada do cérebro.** **CONTROLE** = `claude-opus-5-5` com o prompt de hoje (V0), porque é o primário real do dispatch; **CHALLENGER** = `gpt-6.1-sol` (o sucessor do Sol 6, candidato a primário); **Sonnet 5.5** = o braço barato da Anthropic (mesmo preço do 6.1), só na variante que vencer. O Sol 6 não entra (substituído). ⚠️ O teto de US$ 2 por provedor cortou o controle em 15 das 32 armadilhas e deixou o Sonnet de fora (P-122-03/04) | Opus × 6.1 × Sonnet **85** × 6.1 sozinho **30** (sem controle, nenhum número diz nada) × Sol 6 como controle **40** (não é o de produção) | `evals/bancada.py` (motor `cerebro`) · `reports/SPEC-122-BANCADA.md` · commit `b53ba5a` |
| **D-122-E** | **Evidência — o dispatch CONTINUA no Opus 5.5 primário; o 6.1 fica reserva.** 📊 Bancada de 30/09 (§3.1, recalculada sem modelo): nas mesmas 15 armadilhas, Opus V0 **6** graves × 6.1 V0 **7**; no grupo A o 6.1 responde mais e erra mais (erro 31 % × 23 %). É 2,6× mais barato por chamada, mas **não supera o Opus em segurança**. Com k = 1 a diferença não é significativa — por isso a hipótese conservadora | manter o Opus **88** × promover o 6.1 **30** (troca sem prova em rota que fala com a seguradora) | `reports/SPEC-122-BANCADA.md` §3.1/§4 · `llm_papeis` (dispatch intacto) |
| **D-122-F** | **Evidência — NENHUMA autonomia nova: o cérebro V2 só em SOMBRA, e o `on` é recusado pelo banco.** 📊 G1 (zero erro grave nas armadilhas) falha em todas as variantes; a melhor (V2 no 6.1) fez **2 graves em 31** (trocou o titular num menu reaberto), abstenção correta 90,3 %. Tabela `cerebro_modos` (migration `20260930_02`): `off` \| `sombra` por corretora × seguradora × ramo, nasce **vazia**; em sombra o sistema envia exatamente o de hoje e a divergência vai a `work_events` `cerebro.sombra`. Ligar de verdade exige o critério da proposta (2 semanas ou 50 telas reais sem erro grave) e uma SPEC | sombra governada **90** × ligar a V2 onde ela acertou **15** (G1 é o gate 🔴 do card) × não criar a sombra **45** (a medição real nunca começa) | `acao_do_cerebro.py` · constraint `ck_cerebro_modos_on_recusado_a_bancada_122_nao_aprovou` · commits `582caf3` `501e0ca` · 🧑 ligar é do Founder (P-122-16/17) |
| **D-122-G** | **Gerente (D2 da proposta, mantida) — o passo `sem_chute` sem o dado PERGUNTA ao segurado, onde a URA espera.** Porto, HDI, Yelum e Zurich: pergunta com as opções da tela; a resposta só vira tecla se casar **uma** opção, contra a tela **atual**. Allianz e Alfa (📊 BLOCO 0, 30/09: a URA da Allianz espera 254 s, e 183 s no p10 — a ida e volta de até 3 × 60 s não deixa folga) → pessoa, como antes. Depois do red team: **navegação** (`Voltar`, `Sair`…) nunca é oferecida; passos que **decidem** (serviço aberto da Porto, táxi, submenu de bateria, veículo, motivo) → pessoa; endereço em BR/rodovia/estrada/km nunca vira "Nenhuma das anteriores" sozinho | perguntar onde a URA espera **85** × sempre pessoa **60** (o segurado espera a atendente por um dado que ele sabe) × perguntar em todas **25** (a Allianz fecha antes da resposta) | `insurer_dispatch_service.sem_chute_ao_segurado` · `traduzir_resposta_do_segurado` · `IDA_E_VOLTA_AO_SEGURADO` · commits `582caf3` `501e0ca` · P-122-10/12 |
| **D-122-H** | **Gerente — as novidades da OpenAI de 29/09: só o GPT-6.1 Sol entra agora.** 📊 Laudo do pesquisador (30/09, `GET /v1/models` e páginas oficiais): **Ultrafast** descartado agora (📊 `gpt-6.1-sol-ultrafast` → 404; é *service tier* e só existe no Astra, 6× o preço) · **Agents API** descartada (seria 2º runtime, executor e cofre — CLAUDE.md §5) · **Computer Use** depois (docs divergem; senha de portal num navegador de terceiro) · **Decisions API** não verificada (📊 `/v1/decisions` → 404) · **Plugins, Extensions, MCP Apps, MCP Events** descartar/depois (canal do ChatGPT; rascunho) · **Private Intelligence** e **ZDR com Private Safety Processing** depois (contrato — decisão comercial do Founder) · **Private Inference** não saiu · **Batch/Flex do 6.1 a 50%** depois (trabalho sem pressa, pela fila que já existe). Afirmações do texto externo: "6.1 Ultrafast disponível" e "Private Inference disponível" **erradas**; MCP Apps "de hoje", "ZDR para todos", Decisions e MCP Events "disponíveis" **imprecisas**; Computer Use no 6.1 **não verificada**; "mesmo preço" **certa** | só o 6.1 **88** × adotar Agents API **10** (motor paralelo) × Ultrafast no chat **20** (não existe para o Sol) | `reports/SPEC-122-EXECUTION-REPORT.md` §1.2 |

## D-123-A…M · SPEC-123 — o agente destrava (01/10/2026)

> As leis da SPEC são as D1–D10 do Founder (30/09, `specs-propostas/SPEC-123-…md` §3). Abaixo: o que a EXECUÇÃO decidiu
> com nota (A–J), a K decidida pela execução sob a D5, e o que fica com o Founder (L–M). Relatório `reports/SPEC-123-EXECUTION-REPORT.md` · bancada
> `reports/SPEC-123-BANCADA.md`.

| # | decisão | opções e nota | onde |
|---|---|---|---|
| **D-123-A** | **Gerente (D4, pela regra de empate) — o `gpt-6.1-sol` (high) decide; o `claude-sonnet-5-5` é a 2ª opinião E a reserva.** 📊 Nos 40 casos comuns: 25 × 25 CERTO, 1 × 1 grave (o MESMO caso, `porto-092`); nos 10 com o Opus: 3 × 3 × 3, 0 grave. Diferença ≤ 1 grave e ≤ 5 pontos → o mais barato: 📊 US$ 0,0134/chamada (6.1) × 0,0198 (Sonnet, +48 %) × 0,0423 (Opus, 3,2×). O 6.1 também chama pessoa menos (0 × 3 nos 40) e fica seguro em mais travas D (24 × 21). ⚠️ k = 1 e Opus só em 10 (P-123-03) | 6.1 principal + Sonnet 2ª **88** × Sonnet principal **55** (mais caro, mesmo acerto) × Opus principal **30** (3,2× o preço, n = 10) | `llm_papeis` (`destravador`, `destravador_segunda`) · `SPEC-123-BANCADA.md` §5 · commit `bd9ed3f` |
| **D-123-B** | **Evidência — o DEDUZIR autônomo fica DESLIGADO em código até calibrar** (`DEDUZIR_AUTONOMO_CALIBRADO = False`): a proposta DEDUZIR vira pergunta ao segurado ou pessoa. 📊 Nenhum limiar ≥ 70 chega a 90 % (G3): 6.1 6/14 = 43 % [21–67]; o 6.1 dá nota 90–99 a tudo. Efeito bom: o único grave da bancada vira pergunta → G2 = 0 no produto. CONDUZIR, RESPONDER COM DADO e PERGUNTAR seguem livres | desligar até calibrar **90** × ligar com limiar 99 **35** (📊 3/5 = 60 % no corte mais alto) × sombra só para o DEDUZIR **50** (não mede nada que a bancada não meça) | `destravador.py` · commit `3200228` · reabrir: P-123-01 |
| **D-123-C** | **Gerente — sem `cache_control` na Anthropic.** 📊 A 2ª opinião Sonnet escreveu 8.001–9.824 tokens de cache (1,25× o preço) e leu 1.087–1.698: só compensa se a MESMA sessão chamar de novo em 5 min, o que a 2ª opinião (rara, um caso por vez) quase nunca faz | sem cache **85** × com cache **30** (encarece cada chamada distinta) | `destravador.py` · commit `3200228` (entrou em `e464332`) |
| **D-123-D** | **Gerente (D6) — prazo da pergunta ao segurado por seguradora: 120 s nas de URA apressada, 180 s nas demais.** 📊 Allianz p10 183 s (D-122), Mapfre 2,9 min (n = 1), Alfa 5,2 min (n = 3, amostra pequena), Azul 💭 sem medição → 120 s + 20 s do Vigia fecham ANTES da URA; Porto/HDI/Yelum/Zurich/Bradesco/Tokio esperam ≥ 5 min → 180 s (o de hoje). Seguradora fora da tabela → pessoa (falha fechada) | por seguradora **85** × 180 s em todas **30** (a Allianz fecha antes da resposta) × 120 s em todas **50** (encurta sem motivo onde a URA espera 10 min) | `insurer_dispatch_service.IDA_E_VOLTA_AO_SEGURADO` · `PRAZO_CURTO_NAS_SEGURADORAS` · commit `4488130` · P-123-08 |
| **D-123-E** | **Gerente (D6, depois do juiz B4 ‖ red team B5) — "já existe solicitação" só é adotado como o pedido do caso quando a tela nomeia o MESMO serviço e o "Sim" da confirmação saiu de fato.** 📊 Reprodução: chaveiro × "GUINCHO PESADO" adotava o protocolo do guincho e dizia "Prontinho" ao segurado; agora → pessoa (`ja_existe_solicitacao`). Controle: guincho × guincho → adota. Tela que não nomeia o serviço (hdi) → pessoa | mesmo serviço + "Sim" enviado **90** × adotar qualquer pedido aberto **10** (protocolo falso ao segurado) × nunca adotar, sempre pessoa **55** (perde o caso certo e arrisca duplicar) | `insurer_dispatch_service` (`solicitacao_ja_existente`, `anterior_pode_ter_aberto`) · commit `0fe9080` · P-123-18 |
| **D-123-F** | **Gerente (§9.5) — Allianz auto e Alfa: "Deseja continuar com o CPF/CNPJ 802.###…?" responde SEMPRE "Não, inserir outro".** A tela mostra 5 dos 11 dígitos; dois CPFs com os mesmos 5 abririam o chamado na apólice de OUTRA pessoa (o WhatsApp é da corretora e atende N clientes). 📊 `observed_events` allianz (30/09): nas 2 vezes em que a resposta foi "2", a tela seguinte pediu o CPF — e o caso o tem | sempre "Não, inserir outro" **90** × "Sim" quando os dígitos visíveis batem **60** | `corridor_playbooks._SPEC123_POR_QUE_CONTINUAR["cpf_anterior"]` · commit `4bf04d2` |
| **D-123-G** | **Gerente (D8) — a SEGUNDA CHANCE do agente de atendimento: 1 por conversa por dia, só para dúvida ou dado que falta; a linha do diário é o contador; diário fora do ar → pessoa.** Regra, sinistro, condomínio, empresarial, rota sem corredor e pedido explícito de pessoa passam direto — pelo motivo E pelas falas do segurado (conserto Y, depois do juiz B3 ‖ red team B6). A fase da ficha não trava em `com_humano` | segunda chance contada **85** × sem segunda chance **40** (a D8 do Founder pede) × ilimitada **20** (laço com o segurado) | `human_handoff.por_que_vai_direto_a_pessoa` · commits `74d7614` `090bfbf` `0fe9080` · P-123-13 |
| **D-123-H** | **Gerente (F5 da SPEC, P-121-04) — a carta do portão gravada pelo ESCRITOR OFICIAL de cartas, como `pending_review`.** O destilador publica sozinho o que está em `pending_review` (📊 publicada 01/10 02:29Z, 3 min depois). O texto é o da SPEC: portão eletrônico não é eletricista; raio ou queda de energia que danificou o motor = sinistro de danos elétricos → pessoa | escritor oficial **85** × INSERT direto **30** (a P-121-04 falhou por faltar o `card_hash`) × `proposta_diario` **40** (ninguém publicaria) | `knowledge_cards` `2d28a771…` · commit `3200228` · P-123-12 |
| **D-123-I** | **Gerente (conserto X, juiz B2 ‖ red team B1) — uma opção da TELA só é "dado do caso" pelo slot que o PASSO daquela tela declara.** Antes, "Sim" igual a qualquer slot sim/não do caso furava o DEDUZIR desligado: 📊 60 de 74 telas reais com "Sim" e palavra sensível saíam RESPONDER "Sim" (confirmar resumo divergente, novo atendimento, titular); depois → **0** | slot do passo **92** × igualdade com qualquer slot **10** × nunca aceitar Sim/Não como dado **60** (perde o "Sim, estou no local" legítimo) | `destravador._e_dado_do_caso` · commit `fbb6ebb` |
| **D-123-J** | **Gerente (conserto X, juiz B1 ‖ red team B3) — a pergunta ao segurado é COMPOSTA PELO CÓDIGO a partir da tela, com conferente; o texto do modelo não vai ao segurado.** 📊 Antes: protocolo inventado, taxa por PIX, "cancelado", "garantido", texto para a equipe e pedido de cartão chegavam ao segurado atribuídos à seguradora. Opções irreversíveis (novo atendimento, sinistro, falar com atendente) nunca são oferecidas nem voltam à URA | composta pelo código **90** × texto do modelo com filtros **45** (filtro por palavra sempre deixa uma redação passar) | `destravador.py` · `dispatch_router._opcoes_para_o_segurado` · commit `fbb6ebb` |
| **D-123-K** | ✅ **DECIDIDA pela execução (D5 do Founder: "ligado de verdade por seguradora/ramo, sem período de sombra") — ligar o destravador (`on`) em quais corretoras e seguradoras.** Migration `20261001_02_spec123_destravador_ligado.sql` APLICADA (versão `20261001064837`): 📊 `cerebro_modos` = **40 linhas `on`**, limiar 70, ramo `todos` = 10 seguradoras × as 4 corretoras que têm agente de atendimento (escolhidas pelo banco, `agents.agent_role='attendance'`, nunca por nome); 0 linhas em outro modo. 📊 0 de 4 agentes de atendimento ligados (01/10) → nada acontece até o Founder ligar o agente de uma corretora. Ver / desligar uma seguradora / sombra / desligar tudo: SQL pronto em `TAREFAS-DO-FOUNDER.md` S123.3 | ligado em todas as corretoras com agente, nas 10 seguradoras **85** ✅ × começar por uma seguradora **60** × sombra antes **40** (a D5 dispensou a sombra) | D5 · P-123-14 |
| **D-123-L** | 🧑 **PARA O FOUNDER — o diário guardar a tela COMPLETA (com dado pessoal) para a corretora dona?** Hoje grava só a mascarada; a SPEC F4 pedia "completa na tela do painel para a corretora dona". Exige coluna nova e regra de acesso | coluna nova, visível só à corretora dona **65** × manter só a mascarada **60** (a atendente julga sem ver o dado; menos dado pessoal guardado) — notas próximas: decisão sua | P-123-04 |
| **D-123-M** | 🧑 **PARA O FOUNDER — liberar o DEDUZIR sem calibração?** A sua ordem de 30/09 ("acima de 70 % de certeza, decide") encontrou um modelo que dá 90–99 a tudo e acerta 43 % | manter desligado até calibrar **85** × liberar com limiar 70 **35** (📊 6/14 de acerto nas propostas que agiriam) — já vem decidida pela diferença; confirme se quiser | D-123-B · P-123-01 |

## D-124-A…F · SPEC-124 — o portal de vidros destrava e a visão certa (01/10/2026)

> As leis da SPEC são as D1–D5 do Founder (30/09, `specs-propostas/SPEC-124-…md` §3). Abaixo: o que a EXECUÇÃO decidiu
> com nota (A–E) e o que fica com o Founder (F). Relatório `reports/SPEC-124-EXECUTION-REPORT.md` · bancada
> `reports/SPEC-124-BANCADA-VISAO.md`.

| # | decisão | opções e nota | onde |
|---|---|---|---|
| **D-124-A** | **Gerente (D3, pela regra de empate) — `visao` e `visao_documento` no `gpt-6-luna` medium.** 📊 Bancada por campo, 30 documentos sintéticos, k=3: Luna 100 % · Sol 6.1 (o atual) 100 % · Sonnet 5.5 low 100 % nos campos críticos; empate (0 ≤ 2 pontos) → o mais barato: 📊 ledger sem cache US$ 0,000202 (Luna) × 0,003673 (Sol 6.1) por chamada, ~1/18. ⚠️ Corpus sintético = TETO (0/30 → até ~10 % pelo IC 95 %); fotos reais = P-124-05 | Luna nas duas **88** × manter o Sol 6.1 **45** (18× o custo pelo mesmo acerto medido) × Sonnet 5.5 principal **40** (mesmo acerto, ~27× a Luna) | migration `20261001_03` (`20261001071707`) · commits `1349c39` `217a2c1` |
| **D-124-B** | **Gerente — reserva de OUTRO provedor só na foto (`visao` → Sonnet 5.5 low); `visao_documento` sem reserva.** O docling só fala Chat Completions da OpenAI (`PictureDescriptionApiOptions`, lido no wheel docling-slim 2.130.0); uma reserva Anthropic ali seria uma linha que nunca funciona | reserva só na foto **85** × reserva OpenAI (outro modelo) no docling **50** (não é outro provedor, a D3 pede outro) × reserva Anthropic declarada no docling **15** (falha no dia em que for usada) | migration `20261001_03` · P-124-10 |
| **D-124-C** | **Gerente — o caminho DOM do portal fica FORA desta SPEC.** O DOM roda no contêiner do portal-worker sem `app/` e sem retomada (B0); plugar exigiria HTTP ao smith-api ou retomada nova no DOM — mudança material de escopo. A F1 pluga no API-first (`portal_tool._aguardar`), o caminho que tem retomada (001.10.1) | só o API-first, declarado **75** × HTTP do worker ao smith-api nesta SPEC **55** (contrato novo entre serviços sem nenhuma parada real para provar) × retomada no DOM **35** (reescreve a 001.10.1) | `portal_tool.py` · commit `63595d5` · P-124-01 |
| **D-124-D** | **Gerente (conserto, juiz B1 = red team B1) — a UF desconhecida PERGUNTA ao segurado; nunca outra UF.** A parada só nasce quando a UF que o segurado escreveu não está na lista do portal; qualquer resposta sozinha troca o estado dele (cidade homônima de outro estado). 📊 Antes: "Curitiba" → `{'uf': 'SP'}` com nota 75; depois → `PERGUNTAR_AO_SEGURADO so_o_segurado_sabe`, `resposta ao portal: {}`. Efeito: hoje o portal não responde nenhuma parada sozinho | perguntar **92** × responder só se for a UF do cadastro e estiver na lista **20** (é exatamente o defeito) × chamar pessoa **55** (o segurado sabe responder) | `destravador.CLASSE_DA_PARADA_DO_PORTAL` · commit `c3cd5c7` · P-124-02 |
| **D-124-E** | **Gerente — ordem de deploy do docling: o WORKER antes da API.** API nova + worker antigo → `TypeError` no kwarg `vision` → 2 retries → falha (só com `extract_images=True`; 📊 0 `sanitization_jobs`). O inverso (smith-api novo + docling velho) é seguro: o FastAPI ignora o form extra | ordem escrita na caixa do Founder **85** × compatibilidade no worker (`**kwargs`) **70** (mais um deploy de código para um caminho com 0 uso) | `TAREFAS-DO-FOUNDER.md` S124.1 · P-124-13 |
| **D-124-F** | 🧑 **PARA O FOUNDER — ligar `PORTAL_VIDROS_API_FIRST`?** Sem ele, o destravador do portal não é alcançado (o caminho vivo é o DOM). Ligado, o API-first roda nos pedidos de vidro com as travas de sempre (`PORTAL_REAL_ENABLED`, allowlist, `PORTAL_EFEITO_MATERIAL_LIBERADO`); nas paradas ele PERGUNTA ao segurado ou chama pessoa, e registra no diário. 📊 0 pedidos de vidro desde 01/08 — não há pressa medida | ligar junto com o primeiro canário de vidro, com allowlist **70** × deixar desligado até o próximo pedido real **60** — notas próximas: decisão sua | `vidros_apifirst.py:87` · P-124-01/02 |

## D-125-A…I · SPEC-125 — o atendimento lembra, entende e não pergunta o óbvio (02/10/2026)

> As leis da SPEC são as D1–D10 do Founder (01/10, `specs-propostas/SPEC-125-…md` §3). Abaixo: o que a EXECUÇÃO decidiu com
> nota (B–G) e o que fica com o Founder (A, H, I). Relatório `reports/SPEC-125-EXECUTION-REPORT.md` · medição
> `reports/SPEC-125-DEPOIS.md`.

| # | decisão | opções e nota | onde |
|---|---|---|---|
| **D-125-A** | 🧑 **PARA O FOUNDER (vem decidida, confirme se quiser) — o prompt v2 fica como padrão.** 📊 Luna k=2: v2 77,8 % × base v1 63,9 %; Sol k=1 no DEPOIS (antes dos consertos): v2 8/8 × v1 6/8. O portão do "sim", a máscara de CPF e o corte de terceiro valem nas DUAS versões. Falta a prova pós-conserto no Sol (P-125-01) | manter v2 como padrão **75** × pôr os 4 agentes em v1 até a rodada do Sol **60** (volta ao prompt que mediu pior) | `agents.prompt_versao` · migration `20261001_07` (A) · P-125-09 |
| **D-125-B** | **Gerente (conserto X6) — a parte B da migration `_07` DESCARTADA; a frase contraditória do banco ("colete uma informação por vez") é trocada em CÓDIGO, só na montagem do v2.** Aplicada, a B quebraria a volta exata ao v1 (precisaria do `replace` inverso); e a ferramenta recusou a 1ª aplicação | trocar em código só no v2 **90** × aplicar a B no banco **30** (a volta deixa de ser um UPDATE) × deixar a frase contraditória **20** | `prompts.trocar_a_frase_do_banco_no_v2` · commit `c2414d2` |
| **D-125-C** | **Gerente (conserto Y1, juiz B1) — T8 em CÓDIGO: `insurer_dispatch` só aciona com o "sim" do segurado à pergunta do PRÓPRIO acionamento, lido de `messages` com `company_id`; auto e residencial; fail-closed.** 📊 replay de 27 acionamentos gravados: 0 passariam; na rodada Z, 0 acionamento sem o sim. Preço: ~2,5 turnos a mais e +80 % de custo por conversa (Luna) | portão em código **92** × só o texto do prompt **35** (a LINHA DE BASE mediu 3 acionamentos sem o sim) × só uma checagem na bancada **50** (mede, não impede) | `insurer_dispatch_tool.prova_da_confirmacao` · `23d444a` `fd52568` `3f570a9` `29da022` |
| **D-125-D** | **Gerente (BLOCO 0) — o teto da memória é 40 mil tokens (a SPEC sugeria ~80 mil).** 📊 tokens por conversa de WhatsApp p99 7.957, máx 19.456, 0 acima de 40 mil: 40 mil cobre 100 % das conversas medidas inteiras; acima, resumo do começo, nunca corte calado | 40 mil **88** × 80 mil **70** (o dobro do custo potencial sem nenhuma conversa que precise) | `historico_da_conversa.py` · `3d335b3` |
| **D-125-E** | **Gerente (BLOCO 0) — teto da rajada 45 s, condicionado (só se o último item é foto sem legenda ou ainda chegam itens a < 8 s); o "digitando" continua 25 s.** 📊 22,9 % das rajadas com 2+ mensagens duram > 25 s, p90 46 s | 45 s condicionado **85** × manter 25 s **55** (8 fotos + explicação viram 2 respostas) × 60 s fixo **60** (toda mensagem única espera mais) | `message_buffer_service.py` · `c0d5b4a` |
| **D-125-F** | **Gerente (conserto X, red team B1/B2, juiz B2) — dado de terceiro cortado em CÓDIGO na consulta da apólice (com a flag `POLICY_INTELLIGENCE_V2` em qualquer valor) e CPF mascarado na SAÍDA ("final 4725").** O CPF de outro assunto só volta inteiro depois de o segurado confirmar | código **90** × só a regra do prompt **30** (📊 a LINHA DE BASE revelou a apólice da mãe ao filho, C16 2/2) | `infocap_tool.de_quem_e_a_apolice` · `nodes.mascarar_documentos_na_saida` · `c2414d2` `3f570a9` |
| **D-125-G** | **Gerente (conserto Y3, juiz P3) — o gatilho "corretora nova nasce com o destravador ligado" só age na criação do agente ou quando o papel MUDA.** Assim, apagar a linha (o desfazer do D9) não é desfeito por um re-save | só na criação **88** × em todo UPDATE **30** (recria o que a corretora apagou) | migration `20261002_01` · P-125-11/12 |
| **D-125-H** | 🧑 **PARA O FOUNDER — o D7 ficou pela metade: aceitar?** Dos 4 momentos, `chamou_pessoa` e `respondeu_regra` escrevem; `deduziu` e `nao_chamou_pessoa` não têm sinal confiável sem LLM. Dos 4 sinais de erro leve, só "o agente repetiu a pergunta" | aceitar agora e ligar quando a ferramenta declarar a origem do dado **65** × exigir os 4 antes de ligar um agente **50** (atrasa o ligar por um registro) × ligar com um classificador LLM **40** (custo por turno, régua de outro dialeto) — notas próximas: decisão sua | `nodes.py` (mapa D7) · P-125-06 |
| **D-125-I** | 🧑 **PARA O FOUNDER — orçamento para a rodada do Sol pós-conserto (P-125-01).** 📊 o orçamento da SPEC acabou (US$ 3,7042 de 4,00). 💭 ≈ US$ 1,30 OpenAI: Sol k=1 nos 6 críticos + C4, C8, C11, R1 | autorizar antes de ligar um agente **85** × ligar sem a rodada **40** (a v2 entra no ar sem prova pós-conserto no modelo que atende) | P-125-01 · TAREFAS T-82 |

## D-126-A…J · SPEC-126 — o atendimento quase sem erro (03/10/2026)

> As leis da SPEC são as D1–D7 do Founder (02/10, `specs-propostas/SPEC-126-o-atendimento-quase-sem-erro.md` §3). Abaixo: as
> que a SPEC trouxe decididas (A, B, C) e o que a EXECUÇÃO decidiu com nota (D–J). Nenhuma fica aberta para o Founder; as verbas
> que destravam as pendências estão no T-98. Relatório `reports/SPEC-126-EXECUTION-REPORT.md` · medição `reports/SPEC-126-DEPOIS.md`.
> ⚠️ Em E, F e G a nota é a do gerente; o texto das opções perdedoras foi reescrito a partir dela. Em H, I e J o gerente não deu
> nota numérica: valem pela regra da SPEC §9 ("na dúvida, UMA confirmação a mais é o lado seguro do T8").

| # | decisão | opções e nota | onde |
|---|---|---|---|
| **D-126-A** | **SPEC (vem decidida) — teto DURO de US$ 4,50 de OpenAI para 125 + 126 + 127, com ordem de corte 127-P5 → U6 → final do Sol; nunca cortar a U0 nem a bancada do ok.** 📊 cumprido até aqui: US$ 4,2796 (ledger `service_type='bancada'` desde 02/10 18:50Z, lido 03/10). O corte que aconteceu: a rodada C do Sol e a rodada paga da U6 | teto 4,50 com corte **85** × a conta inteira (💭 ≈ 5,10) **60** | SPEC §8 · relatório G9 |
| **D-126-B** | **SPEC §3.1 (D5 do Founder) — o "ok" aciona só se o CLASSIFICADOR (papel `confirmacao`, gpt-6-luna) E a regex concordarem; botões onde o canal provar.** Os botões ficaram DESLIGADOS: nenhum provedor anuncia `interactive` e o corpo do `/send/button` não foi transcrito. 📊 bancada 179 casos: combinado 0/294 falso ok, 97,9 % ok aceito | classificador + regex **92** × botões **90** (só com aparelho real; P-126-05) × só regex ampliada **55** | `insurer_dispatch_tool.prova_da_confirmacao` · `8d603df` · migration `20261002_11` |
| **D-126-C** | **SPEC (vem decidida) — as apólices do PRÓPRIO titular contam como UMA no aviso de abuso** (o segurado com auto + casa + vida não dispara o alarme). Aplicada | uma pelo titular **88** × o D2 literal (cada apólice conta) **60** | `consultas_por_telefone.unidade` · `9019783` |
| **D-126-D** | **Gerente — o rastro do aviso de abuso fica em `tool_invocations` (pseudônimos HMAC no `output_summary`), sem tabela nova** (CLAUDE.md §5: consolidar antes de criar; o índice `(company_id, created_at)` já existia) | `tool_invocations` **78** × tabela nova de consultas **72** | `consultas_por_telefone.py` · P-126-10/11 |
| **D-126-E** | **Gerente — a U6 NÃO roda a rodada paga do DEDUZIR.** 📊 a porta tem 32 casos, ≤ 5 por seguradora; com n ≤ 5 nenhuma seguradora chega ao n = 10 que a regra exige, então a rodada gastaria sem poder religar nada | não rodar agora **80** × rodar com o n que há **55** × baixar o n mínimo para religar **40** | `destravador.py` · `16d9a68` · P-126-06 · P-123-01 |
| **D-126-F** | **Gerente (U4) — "cobrou o polimento por fora" (reclamação de cobrança do prestador) vai à PESSOA (R9 K2), sem segunda chance** | pessoa na hora **80** × segunda chance **50** | `pos_acionamento.py` (K2) · `076bb53` |
| **D-126-G** | **Gerente (U5) — se o 1º turno foi só segurança + chamar pessoa, a apresentação sai no 2º turno** (uma vez por assunto) | apresentação no 2º turno **80** × apresentar junto da pessoa no 1º **55** | `nodes.py` (apresentação por intenção) · `a803215` |
| **D-126-H** | **Gerente — 👌 NÃO é "ok"; 👍 é.** 👌 também quer dizer "entendi"; na dúvida, uma confirmação a mais | 👌 fora (lado seguro do T8) × 👌 como ok — sem nota numérica | bancada do ok · `insurer_dispatch_tool` |
| **D-126-I** | **Gerente — dúvida ou pergunta DEPOIS do "sim" derruba o sim** ("sim, quanto custa?", "sim?") | derrubar (lado seguro) × aceitar o sim e responder a dúvida — sem nota numérica | conserto Y `a5b1dac` |
| **D-126-J** | **Gerente — "pode ser" e "tudo certo" ficam `outra_coisa`** (o classificador as recusa); medir no acervo antes de mudar | não aciona (lado seguro) × aciona — sem nota numérica | P-126-18 |

## D-127-A…G · SPEC-127 — o portal de vidros no nível do WhatsApp (03/10/2026)

> As leis da SPEC são as D1–D5 do §3 dela (`specs-propostas/SPEC-127-o-portal-de-vidros-no-nivel-do-whatsapp.md`). Abaixo, o
> que a EXECUÇÃO decidiu com nota — A a E no BLOCO 0 (laudo `B0-127`), F na P5, G no conserto único. Nenhuma fica aberta para
> o Founder; as verbas e o canário estão em T-99…T-103. Relatório `reports/SPEC-127-EXECUTION-REPORT.md`.

| # | decisão | opções e nota | onde |
|---|---|---|---|
| **D-127-A** | **Gerente (BLOCO 0) — a retomada R3 do DOM (P7) fica ADIADA, como pendência.** Sem população: a Bradesco é proibida de escrever pela API (D-E00110-05) e "API fora" impede o R3 por definição; gatilho: o canário medir DOM > 0 com a API respondendo | fazer agora **25** (sem população) × adiar com gatilho — o gerente não deu nota ao adiar | P-127-02 |
| **D-127-B** | **Gerente (BLOCO 0) — a P6 vira só a CONTENÇÃO, dentro do P2:** o DOM nunca escolhe peça/causa/lado/reparo/oferta sozinho e para com a tela e as opções reais. A ponte HTTP completa (endpoint novo + variáveis novas no worker + 2 tenants, para um caminho sem replay) fica adiada | contenção no P2 **80** × ponte HTTP agora **40** | `adaptive.py` · `1702b98` · P-127-01 |
| **D-127-C** | **Gerente (BLOCO 0) — a dedup do portal (`atendimento_aberto_existente`) é consultada logo DEPOIS do POST, como a própria tela faz.** 📊 0 de 7 HAR a chamam antes do POST; ela leva o token que nasce no POST | depois do POST **75** × antes, tratando 401 como "não sei" **45** × não chamar **20** | `vidros_apifirst.py` · `2253cf8` |
| **D-127-D** | **Gerente (BLOCO 0) — faltou dado antes da escrita = parada pré-fronteira `etapa="abertura"` + ramo novo na `vidros_continuacao`** que recomeça a abertura no MESMO job (nada foi escrito; o guarda da fronteira A continua valendo) | ramo "abertura" **82** × marcar `failed` e abrir outro job **50** × manter a queda no DOM **10** | `vidros_continuacao.py` · `2253cf8` |
| **D-127-E** | **Gerente (BLOCO 0) — o `portal_action` passa pelo MESMO portão do ok da SPEC-126 (resumo + ok, regex E classificador) antes de criar o job.** 📊 medição final da 126: o R2 abria vidro no 1º turno sem perguntar (2/2). O conserto acrescentou a amarra: o ok tem de ser DESTE pedido (linha pronta, ou peça + cidade + UF + final da placa) | o mesmo portão — sem nota numérica (a regra da 126) | `portal_tool.py` · `insurer_dispatch_tool.confirmacao_comprovada` · `7362725` · P-126-22 |
| **D-127-F** | **Gerente (P5) — a bancada do portal NÃO roda paga.** Sobravam 💭 ≈ US$ 0,22 do teto de 4,50; a Yelum sozinha custaria 💭 0,29–0,72 e a Porto (📊 n = 5 < 10) nunca religaria → DEDUZIR do portal = 0, declarado | não rodar **85** × rodada parcial **40** | `bancada_portal.py` · `672441f` · P-127-04 · T-102 |
| **D-127-G** | **Gerente (conserto único) — (1) o vigia respeita a TABELA do destravador** (não relê a parada que ele conduz); **(2) texto honesto à equipe** quando o recomeço da abertura falha ("abra DIRETO no portal, uma vez") | (1) respeitar a tabela **78** × tirar o estágio dos técnicos **65** · (2) texto honesto **72** × retomada automática **60** × liberar a chave do pedido **55** | `vigia_do_portal.py` · `portal_params.py` · `7362725` |

## D-MC-08…50 · PROGRAMA MULTICÁLCULO (04/10/2026) — a fila nova, registrada no passo 0.5

> Fonte: [`programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md`](programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md) §2 (v2.4,
> cópia fiel do anexo do Founder, 📊 sha256 `6cebc63c…` igual ao original). O texto completo de cada decisão, com a
> consequência, está lá; aqui fica o ESTADO. Origem "Amandus" ou "por delegação" = **TOMADA**; "Recomendação" =
> **PROPOSTA**, confirmada pela execução na SPEC de cada uma quando os fatos sustentarem (D-MC-49).
> Prefixo D-MC- porque D8–D22 já existem neste arquivo com outro sentido.

| # | Decisão (resumo) | Estado | Substitui / revê |
|---|---|---|---|
| D-MC-08 | Um computador para tudo do AutoBrokers; fila em linha reta | ✅ TOMADA (Amandus) | — |
| D-MC-09 | Agger é o multicálculo oficial; outros entram como adaptador da mesma porta | ✅ TOMADA (Amandus) | — |
| D-MC-10 | CPF obrigatório no Agger; CPF falso fora de questão; a apólice é a melhor entrada | ✅ TOMADA (Amandus) | — |
| D-MC-11 | Começar com 1 usuário robô, depois 2 | ✅ TOMADA (Amandus) | — |
| D-MC-12 | Escala: várias corretoras, vários robôs, vários multicálculos | ✅ TOMADA (Amandus) | — |
| D-MC-13 | Qualquer corretora cota qualquer ramo (v1 = auto) | ✅ TOMADA (Amandus) | — |
| D-MC-14 | 💭 (estimativa da equipe) 3 em 5 renovações pedem ajuste, quase sempre de preço | ✅ TOMADA (Amandus) | — |
| D-MC-15 | Fases P1 humano envia · P2 agente negocia · P3 agente fecha | ✅ TOMADA (Amandus) | — |
| D-MC-16 | Todo cálculo fica registrado (refinada pela D-MC-31) | ✅ TOMADA (Amandus) | — |
| D-MC-17 | Custo por cálculo o menor possível, sem erro | ✅ TOMADA (Amandus) | — |
| D-MC-18 | Nenhuma corretora em destaque na busca; a vencedora no fim | ✅ TOMADA (Amandus) | — |
| D-MC-19 | Cobrança, parecer jurídico e copy ficam para depois | ✅ TOMADA (Amandus) | — |
| D-MC-20 | Isca no site só se o canal travar | ✅ TOMADA (Amandus) | — |
| D-MC-21 | A 001.9 não é prioridade | ✅ TOMADA (Amandus) | — |
| D-MC-22 | Marca de consumo: **Quem Cobra Menos** | ✅ TOMADA (Amandus, 04/10) | — |
| D-MC-23 | Uso do Agger com a autorização da corretora que tem o contrato; sem pedido de anuência ao Agger agora | ✅ TOMADA (Amandus) · 04/10 o Founder declarou a autorização escrita de Resulta e AutoFleet para concluir cálculos | **substitui a D-E002-01** e a tarefa H.2 |
| D-MC-24 | Usuário robô dedicado por corretora; nunca o login de uma pessoa no motor | ✅ TOMADA (delegação) | confirma a D-E002-02 |
| D-MC-25 | A AutoBrokers opera o canal; cada corretora controla as próprias oportunidades | ✅ TOMADA (Amandus, provisória) | — |
| D-MC-26 | Canal = catálogo global + adesão por corretora + registro mínimo numa empresa técnica | ✅ TOMADA (delegação) | — |
| D-MC-27 | A InfoCap da Resulta na Amandus foi intencional; volta à Resulta antes da 131 | ✅ TOMADA (Amandus) | fecha a dúvida da P-E002-X1 |
| D-MC-28 | Transporte: interceptação como padrão | ⏳ PROPOSTA · ✅ **a parte "chamadas de dentro da página só com autorização expressa do Founder" foi RESOLVIDA em 05/10 pela D-128-03 (TOMADA):** o recálculo reenvia o corpo do pedido de dentro da página; o login continua pela tela; a interceptação continua lendo os resultados | — |
| D-MC-29 | Preço do canal por termo com cada corretora | ⏳ PROPOSTA (portão de preço da 133-B) | — |
| D-MC-30 | Porta do piloto: convite revogável + wa.me + teto + interruptor | ⏳ PROPOSTA · 🔁 revista em 05/10 (D-MC-51): no WhatsApp, lista de números convidados + limite por número | revê a D-E007-03 no piloto |
| D-MC-31 | Contato futuro só com consentimento; anonimizar após N dias | ⏳ PROPOSTA | refina a D-MC-16 |
| D-MC-32 | A 135 liga depois de N propostas medidas na fase 1 | ⏳ PROPOSTA | revê a D-E002-04 |
| D-MC-33 | No piloto, o canal usa o robô da corretora de registro, com prioridade ao vivo | ⏳ PROPOSTA · 🔁 revista em 05/10 pela D-MC-56 (várias corretoras em paralelo) | revê a D-E007-06 no piloto |
| D-MC-34 | Páginas do cliente "uau", com modelo visual aprovado antes da 130 | ✅ TOMADA (Amandus) | — |
| D-MC-35 | Segredos e o apagar das gravações do intake: o Founder cuida fora do programa; não bloqueiam SPEC | ✅ TOMADA (Amandus) | — |
| D-MC-36 | Prova de instalação cedo (133-A) | ✅ TOMADA (Amandus) · 🔁 revista em 05/10 (D-MC-51): a prova de instalação vai para a ★; a 133-A passa a ser o WhatsApp | — |
| D-MC-37 | O cálculo não se chama "quote" no código; porta `MulticalculoProvider` | ⏳ PROPOSTA | — |
| D-MC-38 | A fila do plano substitui a ordem da D-FILA-01 e a D-E002-07 | ✅ TOMADA (Amandus) | **substitui a D-FILA-01 (ordem) e a D-E002-07** |
| D-MC-39 | O conhecimento destilado continua GLOBAL; a P-E0018-14 só garante que saia anônimo; nunca `company_id` na `conduct_playbooks` | ✅ TOMADA (Amandus) | — |
| D-MC-40 | 129-B prova isolamento com 1 robô por corretora; o roteador entre corretoras nasce na 133-B | ✅ TOMADA (delegação) · 🔁 revista em 05/10 pela D-MC-56: o paralelo entre corretoras entra na 129-B; na 133-B, só as regras de negócio | — |
| D-MC-41 | O recálculo volta à conta da corretora, não ao mesmo login | ✅ TOMADA (delegação) | — |
| D-MC-42 | Fila e navegador próprios para o cálculo | ✅ TOMADA (delegação) | — |
| D-MC-43 | PDF da proposta num render próprio, fora do navegador do cálculo | ⏳ PROPOSTA (decide a 130-A) | — |
| D-MC-44 | Proposta com 2 opções por padrão (completa e econômica) | ✅ TOMADA (Amandus) | — |
| D-MC-45 | Portão de preço na abertura da 130-A e da 133-B | ✅ TOMADA (Amandus) | — |
| D-MC-46 | Barrar CPF de outra pessoa (declaração + nome da apólice × nome do cadastro, nunca mostrado) | ✅ TOMADA (delegação) | — |
| D-MC-47 | O robô marca os negócios que cria e não recalcula negócio mexido por pessoa há < 24 h | ✅ TOMADA (delegação) | — |
| D-MC-48 | Os consertos do passo 0.5 seguem o rito CRÍTICO | ✅ TOMADA (delegação) | — |
| D-MC-49 | Execução contínua, SPEC atrás de SPEC, parando só nos portões e no CLAUDE.md §10 | ✅ TOMADA (Amandus) | — |
| D-MC-50 | Narração ao vivo honesta: cada frase nasce de um evento real | ✅ TOMADA (Amandus: a ideia; o desenho é da 133-B) | — |

**Verba (Founder, 04/10):** 💭 US$ 4 de API de modelo para as primeiras SPECs do programa. Cada gasto vai ao livro-caixa em
`programa-multicalculo/ESTADO-DO-PROGRAMA.md`. Nenhuma rodada paga sem estimativa antes.

## D-129A-1…10 · SPEC-129-A — a espera durável (04/10/2026, tomadas pela execução com nota 0–100; rito AAA v13 CRÍTICO)

> D-129A-1 a D-129A-7: texto e notas na SPEC (`specs/SPEC-129-A-a-espera-duravel.md` §3) — espera = `waiting_input` + `wake_at`/`wait_for`
> só `smith` (85) · acorda no laço de órfãos que já existe (85) · CAS por UPDATE filtrado + re-despacho que se cura (82) · passo EXTERNO
> interrompido não repete → `efeito_incerto` (D-129A-4) · idade-limite 2 h por `requested_at` (D-129A-5) · o retrato cru do acionamento só
> enquanto restaurável (D-129A-6) · `needs_human` do portal com backoff 5→60 min (D-129A-7).

| # | Decisão | Notas | Onde |
|---|---|---|---|
| **D-129A-8** | **Passo `efeito="nenhum"` sem `guardar` continua re-executando na retomada** (intelligence, research, claims, susep, bridge.auxiliary): devolver `None` quebraria quem usa o resultado; repetir não envia nada para fora do banco (📊 juiz: grep de envio nos 5 módulos → 0; red team: o único que manda WhatsApp, o briefing, é idempotente por período) | re-executar **80** × pular todo passo concluído **50** | `workflows.py` (F2) |
| **D-129A-9** | **Passo EXTERNO sem prova de estado não roda → `EtapaNaoVerificada`** (nada saiu do prédio) → `retry_scheduled` 60 s; a idade de 2 h encerra | `EtapaNaoVerificada` **85** × `EfeitoIncerto` **60** (avisaria "pode ter acontecido" sem ter acontecido) | `runs.py`, `workflows.py`, `smith_worker.py` (conserto) |
| **D-129A-10** | **Cancelamento pedido termina `cancelled`** (exceção própria `CancelamentoPedido`, herdeira de `CancelledError`); desligamento real segue `retry_scheduled` | exceção própria **88** × consultar `cancel_requested_at` no except **70** | conserto único |

## D-128-01…08 · SPEC-128 — a prova do Agger (04/10/2026, tomadas pela medição com nota 0–100; rito AAA v13 CRÍTICO)

> Texto e números em `programa-multicalculo/A-PROVA-DO-AGGER.md` §5 (e §3, pergunta a pergunta). D-128-01, 02 e 04…08: ✅ TOMADAS
> (delegação, D-MC-49). ✅ **D-128-03: TOMADA pelo Founder em 05/10/2026** (era PROPOSTA; resolve a D-MC-28; fecha a P-128-14 e a T-107).

| # | Decisão | Notas | Onde |
|---|---|---|---|
| **D-128-01** | ✅ **As alavancas foram medidas na AutoFleet** (configuração real de automóvel, comissão-base 15 %), não na Resulta (comissão 0) | AutoFleet **88** × Resulta **60** | A-PROVA §3 E5 |
| **D-128-02** | ✅ **Família nova de resposta: DADO** — pedido a corrigir ("calcule como renovação", "DMO obrigatória", "CEP inválido") não é recusa do risco | DADO **85** × encaixar em ACEITACAO **50** | `multicalculo/contrato.py`, `leitor_agger.py` |
| **D-128-03** | ✅ **TOMADA (Founder, 05/10/2026) — o recálculo é o corpo do pedido:** o robô recalcula REENVIANDO o corpo do pedido (`calcularV2`) com o ajuste, de dentro da página, com o token do próprio app, em vez de clicar no formulário. Isso resolve a parte da **D-MC-28** que pedia a autorização expressa do Founder para chamadas de dentro da página: **o login continua pela tela; a interceptação continua lendo os resultados**. A medição já fez assim (📊 recálculos da E5, E7 e E20, n = 11 versões válidas) sob a autorização ampla do Founder de 04/10 para validar · ~~⏳ PROPOSTA~~ | corpo do pedido **88** × interceptar e clicar **70** | A-PROVA §5 · P-128-14 ✅ FECHADA · T-107 ✅ · 129-B |
| **D-128-04** | ✅ **Proposta de 2 opções = 2 cálculos** (📊 1 pacote por cálculo, E20; o plano é "ilimitado") | **90** | A-PROVA §3 E20 |
| **D-128-05** | ✅ **O motor manda as coberturas explícitas, nunca o pacote da conta** (📊 o "Prata" difere entre corretoras, E8) | **92** | contrato `PedidoDeCalculoAuto.coberturas` |
| **D-128-06** | ✅ **O motor entrega aos poucos e fecha por tempo** (💭 90 s), sem esperar a seguradora calada (📊 26 de 227 nunca fecharam) | **88** | contrato `eventos_entre` → 129-B |
| **D-128-07** | ✅ **Renovação = InfoCap + Agger pela placa/CPF + padrões do questionário marcados como "assumido"**, para o corretor conferir | **80** | A-PROVA §3 E2 → 131 |
| **D-128-08** | ✅ **O adaptador da 129-B herda a lista branca do captador:** a única escrita é o cálculo | **90** | A-PROVA §7 → 129-B |

## D-MC-51…60 · PROGRAMA MULTICÁLCULO — o Quem Cobra Menos vira WhatsApp, plano A (05/10/2026)

> Fonte: [`programa-multicalculo/PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md`](programa-multicalculo/PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md) §2
> (o porquê de cada uma) · plano mestre **v2.5** §2. Tomadas pelo Founder na conversa que fechou a SPEC-128 (04–05/10), exceto a
> D-MC-57, que é HIPÓTESE dele, não decisão. Revêem a D-MC-30, a D-MC-33, a D-MC-36 e a D-MC-40 (marcadas acima) e a condição
> "teto por seguradora" da 133-B.

| # | Decisão (resumo) | Estado | Substitui / revê |
|---|---|---|---|
| D-MC-51 | **WhatsApp é o plano A** do Quem Cobra Menos (zero instalação; o telefone identifica a pessoa; foto da apólice natural; passagem à corretora na mesma conversa; o mesmo número serve aos lembretes da 136). Claude/ChatGPT ficam para depois (★). Notas: WhatsApp 88 · Claude/ChatGPT primeiro 62 · os dois juntos 50 | ✅ TOMADA (Founder, 05/10/2026) | revê a D-MC-36 e a 133-A |
| D-MC-52 | **Fase 1 no WhatsApp comum (Evolution Go), número EXCLUSIVO da marca; fase 2 na API oficial (SPEC-134)** quando a Meta aprovar empresa, número e nome. Risco de bloqueio aceito (estrutura temporária; piloto só com Resulta e AutoFleet); o canal é uma borda e a troca de transporte não muda a conversa. 📊 Preço Meta desde 01/10/2026: respostas pagam após 1.000 grátis/mês/número, Brasil ≈ US$ 0,0068 (periskope.app e callbell.eu, 04/10/2026 — conferir na tabela oficial antes da 134) | ✅ TOMADA (Founder, 05/10/2026) | a 134 vira a migração |
| D-MC-53 | **Nenhum limite por seguradora por dia no início**; só medir (cálculos por seguradora por dia, recusas); a regra volta se o volume crescer | ✅ TOMADA (Founder, 05/10/2026) | revê a condição "teto por seguradora" da 133-B |
| D-MC-54 | **A econômica é rascunho.** No portão de preço (abertura da 130-A) o agente PERGUNTA ao Founder e traz as ideias medidas (A-PROVA-DO-AGGER §3 E5) e a "margem da corretora" (comissão e desconto como uma regra, com piso; o motor escolhe o botão por seguradora) | ✅ TOMADA (Founder, 05/10/2026) | detalha a D-MC-45 |
| D-MC-55 | **O Quem Cobra Menos não é corretora:** marca/serviço do AutoBrokers que compara seguradoras E corretoras parceiras (poucas, todas clientes do AutoBrokers; no início só Resulta e AutoFleet) e entrega a corretora VENCEDORA. Comunicação honesta ("comparador independente; a contratação é feita pela corretora parceira vencedora, registrada na SUSEP"); texto final na fase de copy | ✅ TOMADA (Founder, 05/10/2026) | — |
| D-MC-56 | **Cotação em várias corretoras em PARALELO** (um robô por corretora, na conta dela; o tempo é o da mais lenta). As regras de negócio entre corretoras (empate, rodízio, quantas por pedido, o que a parceira paga) são do Founder, portão da 133-B. ⚠️ Hipótese a MEDIR na 129-B: o mesmo CPF vindo de 2+ corretoras | ✅ TOMADA (Founder, 05/10/2026) | revê a D-MC-33 e a D-MC-40 |
| D-MC-57 | **Modelo comercial:** as parceiras pagam mensalidade + o custo de API de cada cotação. Nenhum preço entra no código antes da decisão (CLAUDE.md §13.6, SPEC-062) | 💭 **HIPÓTESE do Founder — NÃO decidida** | — |
| D-MC-58 | **O número do Quem Cobra Menos é separado do atendimento das corretoras** e não espera "ligar o atendimento". Mesma estrutura do AutoBrokers (integração WhatsApp, webhook, agente, roteador de modelos), nenhum motor paralelo (CLAUDE.md §5); agente de escopo estreito (só cotação); a integração mora na empresa técnica (D-MC-26); as corretoras não precisam de WhatsApp próprio | ✅ TOMADA (Founder, 05/10/2026) | a 134 deixa de esperar a classe A |
| D-MC-59 | **O agente sabe conversar e não força venda:** gatilhos honestos, nunca pressão falsa, nunca "o mais barato do mercado" sem prova (só "das N que cotei", CDC art. 37/38), nunca evento inventado (D-MC-50). O perfil (garagem, uso, km, condutor jovem) é declaração do segurado: o agente PERGUNTA; o que está na apólice vem da apólice | ✅ TOMADA (Founder, 05/10/2026) | — |
| D-MC-60 | **O resultado no WhatsApp:** padrão e econômica calculadas ao mesmo tempo desde o 1º pedido (nota 88); narração real em poucas mensagens; o quadro aos ~30–60 s com quem respondeu (atrasada só avisada se entrar no top 3); uma linha por seguradora + as 2 melhores completas + a econômica do vencedor + "recomendo X (nota/100) porque…" + o link da página "uau" (130-A, `/r/`); mensagens compactas | ✅ TOMADA (Founder, 05/10/2026 — recomendações aceitas) | — |

## D-MC-61 · PROGRAMA MULTICÁLCULO — a fila intercalada, v2.5.1 (05/10/2026, tarde)

> Fonte: [`programa-multicalculo/PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md`](programa-multicalculo/PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md) §3 e §8
> · plano mestre **v2.5.1** §0, §0.1 e §2. O Founder notou que a fila v2.5 empurrava os AUXILIARES das corretoras (131 renovação e
> 132 cotação no chat principal) para depois da 134, que depende da Meta. O programa tem duas linhas, e as duas andam: o Quem Cobra
> Menos (leads novos para as corretoras) e os Auxiliares de Renovação e de Cotação (o dia a dia da corretora, no chat principal).

| # | Decisão | Estado | Substitui / revê |
|---|---|---|---|
| D-MC-61 | **A fila intercalada (v2.5.1):** 129-B → 130-A → 133-A → 130-B → 131 → 132 → 133-B → 135 → 136 → 137 → ★, com a **134 FLUTUANTE**: entra assim que a Meta aprovar, a qualquer momento depois da 133-A, sem segurar ninguém. **Regras de troca:** se o portão da 131 (InfoCap da Resulta de volta na Resulta, D-MC-27) estiver aberto antes do da 130-B (crédito de API + 20–30 apólices), a 131 sobe para logo depois da 133-A; a 132 exige a 130-B (a cotação nova a partir da apólice de outra corretora). **Notas:** intercalada **88** · auxiliares primeiro e Quem Cobra Menos depois **75** · a v2.5 como estava **55** (a 134 depende da Meta e travava os auxiliares). **Por quê:** a 133-A é piloto fechado com 5 testadores e precisa de tempo de calendário (as rodadas de teste rodam enquanto se constroem a 131 e a 132). **Marcos:** 🚀1 renovação no ar (131) · 🚀2 cotação no chat principal (132) · 🚀3 Quem Cobra Menos piloto no WhatsApp (133-B) · 🚀4 negociação pelo WhatsApp (135; ainda exige o atendimento das corretoras ligado e a D-MC-32) · 🚀5 público (137 = o Quem Cobra Menos no WhatsApp oficial aberto; Claude/ChatGPT é a ★, depois) | ✅ TOMADA (Founder/gerente, 05/10/2026, tarde) | substitui a fila da v2.5 (PASSAGEM §3 da manhã) |

## D-MC-62…65 · PROGRAMA MULTICÁLCULO — o portão de preço da 130-A (05/10/2026, madrugada)

> Perguntado pelo gerente durante a SPEC-129-B (D-MC-45/D-MC-54), com os números de `programa-multicalculo/A-PROVA-DO-AGGER.md`
> §3 E5/E16. 🧑 **Ressalva do Founder, nas palavras dele:** *"essas decisões serão usadas agora e no futuro vou fazer alguns
> ajustes pontuais. Perguntei as estratégias dos comerciais das corretoras para cotação econômica, margem, piso e completa e,
> quando tiver as respostas, envio para ver se fazemos alguns ajustes baseado na experiência dos comerciais."* → cada uma é
> CONFIGURAÇÃO (presets/colunas), nunca constante espalhada, para o ajuste futuro ser troca de valor.

| # | Decisão | Estado | Substitui / revê |
|---|---|---|---|
| D-MC-62 | **A econômica padrão** = franquia normal + vidros básicos + carro reserva 7 dias + assistência básica; casco 100 % FIPE e terceiros (RCF/APP) intactos; FIPE a 90 % fora. Notas: esta 85 · só franquia+vidros 70 · agressiva sem reserva 60 | ✅ TOMADA (Founder, 05/10/2026) — ajustável com os comerciais | fecha o rascunho da D-MC-54 (parte "econômica") |
| D-MC-63 | **A margem da corretora** (comissão e desconto como UMA regra): o agente CALCULA a versão com margem menor e a mostra ao CORRETOR; nada vai ao cliente sem o corretor aprovar, cada vez; o motor escolhe o botão por seguradora (comissão, ou desconto onde a seguradora ignora a comissão — 📊 Porto, Azul, Itaú). Notas: propõe+aprova 85 · automático até o piso 65 · nunca mexe 55 | ✅ TOMADA (Founder, 05/10/2026) — ajustável | fecha a D-MC-54 (parte "margem") |
| D-MC-64 | **O piso padrão da margem = comissão de 10 %** enquanto a corretora não configurar o dela. Notas: 10 % 80 · 12 % 70 · sem piso 65 | ✅ TOMADA (Founder, 05/10/2026) — ajustável | — |
| D-MC-65 | **A completa é UM padrão único** para todas as corretoras: RCF 200/200/20 mil, APP 5 mil, franquia reduzida, vidros completos, carro reserva 15 dias, assistência completa (o motor manda as coberturas explícitas, D-128-05) — comparação igual-com-igual entre corretoras. Notas: único 85 · cada corretora a sua 60 | ✅ TOMADA (Founder, 05/10/2026) — ajustável | — |

## D-MC-66…74 · PROGRAMA MULTICÁLCULO — a estratégia das comerciais, a 129-C e o tamanho da resposta no WhatsApp (06/10/2026)

> Confirmadas pelo Founder na abertura da SPEC-130-A (06/10, madrugada), com o texto e as notas de
> `programa-multicalculo/ESTRATEGIA-COMERCIAL-DAS-CORRETORAS.md` §2. 🧑 Nas palavras dele: *"ajustes futuros virão dos comerciais:
> deixe tudo como CONFIGURAÇÃO, nunca constante espalhada"* — vale para D-MC-62…72: cada número (comissão 15/12/10 %, alvo
> 10–15 %, prazos de lembrete, validade) mora numa configuração por corretora com o padrão do produto, nunca no código.

| # | Decisão | Estado | Substitui / revê |
|---|---|---|---|
| D-MC-66 | **Três situações, três estratégias:** renovação (mesmas coberturas na seguradora atual, comissão ≥ a do ano anterior, mirando o preço do ano anterior; + a melhor custo-benefício; + uma "completa+") · novo COM apólice (mesmas coberturas em outra seguradora, comissão 15 % + desconto permitido, alvo inicial ~10–15 % abaixo do preço atual quando der, guardando margem) · novo SEM apólice (econômica + completa, + completa+ quando couber). Notas: 88 × "uma regra só" 55 | ✅ TOMADA (Founder, 06/10/2026) | D-MC-44, D-MC-62 (a econômica continua) |
| D-MC-67 | **A ordem do "mais barato":** ① o desconto que a seguradora permite ② comissão 15 → 12 % ③ franquia maior ④ carro reserva ⑤ vidros/assistência; cobertura só cai DEPOIS da margem e sempre dito ao cliente; 10 % só com concorrência declarada. Notas: 85 × a ordem antiga 65 | ✅ TOMADA (Founder, 06/10/2026) | D-MC-63 (a ordem) |
| D-MC-68 | ✏️ **CORRIGIDA pelo Founder em 06/10/2026, 23h** (*"eu não falei isso"*): ~~10 % só com o corretor aprovando~~ → **o agente desce até o piso de 10 % SOZINHO, sem aprovação humana, mas PASSO A PASSO (1 pp por vez, `comissao.passo_pp`), nunca direto.** De 15 % a 12 % é a negociação normal; **de 12 % a 10 % é a ALAVANCA DE FECHAMENTO**: guardada para o fim, oferecida **em reais** ("falei com a seguradora e consegui R$ X a menos") e só com o cliente fechando — **nunca dita em "%"**. Os limites se ajustam com as ideias das comerciais (config). Notas: como o Founder disse 95 × como estava gravado 20 (gravado errado) | ✅ TOMADA (Founder, 06/10/2026 — corrigida às 23h) | **revê a D-MC-63** (nenhuma aprovação humana dentro da régua) e a D-MC-67 (o 10 % não exige concorrência declarada) · SPEC-130-A.1 |
| D-MC-69 | **"Como a sua apólice atual"** sempre que houver apólice: 3 opções (igual à atual · econômica · completa+ com franquia reduzida e pequenos reparos); sem apólice: 2. Nota 84 | ✅ TOMADA (Founder, 06/10/2026) | D-MC-44 (2 opções) |
| D-MC-70 | **"Usa o carro para aplicativo?" é a 1ª pergunta do perfil**; sim → calcula só nas seguradoras que aceitam e avisa honestamente. Nota 90 | ✅ TOMADA (Founder, 06/10/2026) | D-MC-59 |
| D-MC-71 | **Validade e retorno honestos:** "válido até <data>" = a menor validade das seguradoras do quadro (medir na 130-A); 1 lembrete ~24 h depois em horário comercial + 1 antes de vencer; nunca cronômetro falso; "desconto se fechar hoje" só REAL e aprovado. Notas: 80 × 6/12 h + desconto relâmpago 45 | ✅ TOMADA (Founder, 06/10/2026) | — |
| D-MC-72 | **A cotação-alvo ("fecha por R$ 2.000?"):** o motor procura, na ordem da D-MC-67, a combinação que chega no alvo com a MAIOR comissão possível (1 recálculo por tentativa, várias em paralelo); se só chega cortando cobertura, mostra o que mudou e recomenda (ou NÃO). Nota 80 | ✅ TOMADA (Founder, 06/10/2026) | — |
| D-MC-73 | **SPEC-129-C · mais ramos do Agger** (Condomínio, Empresarial e Residencial primeiro — 📊 A-PROVA-DO-AGGER §10: a Resulta tem 672 · 182 · 115 negócios nesses ramos em 2 anos e 14 de auto) entra na fila **logo depois da 133-A e antes da 131**. O mesmo motor e montador da 129-B, um pedido e um preset por ramo — nunca um motor novo. Notas: depois da 133-A **85** × antes da 133-A 72 (a 133-A é de auto e o WhatsApp precisa de calendário com os testadores) | ✅ TOMADA (Founder, 06/10/2026) | D-MC-61 (a fila ganha a 129-C) |
| D-MC-74 | **O tamanho da resposta no WhatsApp:** a mensagem leva **no máximo 2 opções** (a recomendada e a mais em conta, uma linha de "por quê" cada) + **1 linha-resumo** ("cotei em N seguradoras; X responderam") + **o link**, cuja prévia (imagem gerada por proposta, sem dado pessoal) já mostra o melhor preço. A lista de todas as seguradoras e as 3 opções por situação (igual à atual · recomendada · econômica, D-MC-69) ficam na **página**, num **carrossel de arrastar para o lado** (o cartão seguinte aparece pela borda), com "comparar lado a lado" para quem quiser a tabela. Notas: 2 no WhatsApp + carrossel de 3 na página **90** · 3 opções no WhatsApp 70 · lista completa + 2 no WhatsApp (a D-MC-60 como estava) 58 · só o link 55 (sem nenhum preço na conversa, o link parece golpe e perde o "uau"). Por quê: no celular, ninguém lê 14 linhas de preço; empilhar cartões obriga a rolar e esquecer o primeiro; arrastar compara um a um com o dedo — o Founder pediu (06/10) e é o padrão das lojas de app e dos comparadores de celular | ✅ TOMADA (gerente da 130-A com o Founder, 06/10/2026 — análise pedida por ele) | **revê a D-MC-60** (a parte "uma linha por seguradora no WhatsApp") |

## D-130A-06…11 · SPEC-130-A — a pergunta única da abertura (06/10/2026, 07:40)

> O gerente da 130-A perguntou UMA vez (o modelo visual e três itens de escopo da ficha); o Founder escolheu as quatro recomendações.

| # | Decisão | Estado | Substitui / revê |
|---|---|---|---|
| D-130A-11 | **O modelo visual da página da proposta = a direção "carteira"** (passes de carteira picotados, só a recomendada na cor da marca, carrossel de arrastar com o próximo cartão aparecendo, régua só das completas, comparar lado a lado, funciona sem JavaScript). Painel cego de 4 rodadas, 8 críticos frescos: 85/83 → 89/88 → 90/92 → 91/90 (conversão/acabamento); as outras direções 81/77 (precisão) e 68/74 (conversa). Os 8 acabamentos medidos da 4ª rodada entram na versão de produção. Protótipo: claude.ai/artifact/K3pGqdMQ9dvThA7r6AZSZC | ✅ TOMADA (Founder, 06/10/2026) | — |
| D-130A-06 | **Registro do lead e do consentimento vão para a 133-A**, onde a conversa do WhatsApp colhe o "sim"; na 130-A a proposta publicada + o pedido são o registro da oportunidade. Notas 80 × já na 130-A 55 | ✅ TOMADA (Founder, 06/10/2026) | a ficha da 130-A (plano §4) |
| D-130A-07 | **PDF da proposta = o "imprimir/salvar PDF" do navegador** (CSS de impressão); o PDF gerado no servidor fica para quando houver render fora do robô (D-MC-43). Notas 75 × já 50 | ✅ TOMADA (Founder, 06/10/2026) | a ficha da 130-A |
| D-130A-08 | ❌ **REVOGADA pelo Founder em 06/10/2026, 23h:** *"isso não será feito. Nós não vendemos seguros; nós só informamos através da tecnologia."* ~~A remuneração da corretora (Res. CNSP 382) como opção da config, desligada até o jurídico~~ → a opção sai da config e do modelo da página; a T-127 e a P-130A-16 fecham | ❌ REVOGADA (Founder, 06/10/2026) | SPEC-130-A.1 |

| # | Decisão (gerente da 130-A, 06/10/2026 — registradas na SPEC §10) | Estado | Substitui / revê |
|---|---|---|---|
| D-130A-09 | **A 3ª opção:** sem apólice → Recomendada · Mais em conta · Mais completa (completa+ quando calculada; sem ela, "Outra completa"/"Menor franquia"); com apólice → a Recomendada (a melhor completa, para o título nunca mentir — conserto RT-B1) + Igual à sua atual + Mais em conta (P-130A-22 decide a completa+ na 131) | ✅ TOMADA (gerente, nota 80) | D-MC-69 (ajustada pelo RT-B1) |
| D-130A-10 | **O artefato da proposta mora no SOLICITANTE** (a corretora no pedido dela; o canal no pedido do canal); a marca da anfitriã vai no modelo da página. Notas: 85 × na anfitriã 45 | ✅ TOMADA (gerente) | — |

| # | Decisão (SPEC-130-A.1 e o retorno do Founder, 06/10/2026 noite — o Founder pediu: decidir pela maior nota e avisar no fim) | Estado | Substitui / revê |
|---|---|---|---|
| D-130A1-01 | **A mensagem do CANAL é outra função, escolhida pela ORIGEM do pedido.** A proposta da carteira (renovação e cotação das corretoras) continua a da 130-A e **nunca** menciona o Quem Cobra Menos. Notas: duas funções 93 × uma com chave 70 | ✅ TOMADA (gerente, nota 93) | D-MC-74 (para o canal) |
| D-130A1-02 | **"Cotações realizadas" = o número REAL de preços que voltaram** no pedido (todas as ofertas das OPÇÕES, de todas as corretoras — nunca os recálculos da negociação). 📊 o canário de 05/10 teve 82 preços nas opções em 495 s (o 104 que constava somava 22 preços de recálculo — pego pelo juiz e pelo red team, 07/10). A fórmula sugerida ("seguradoras × 3 × corretoras + 100") **não entra**: o +100 é um número que não aconteceu, dito ao consumidor (CDC art. 37; o art. 67 tipifica) — e o produto vende confiança ("só aceite Nível 5"). O número real cresce sozinho com cada corretora nova. Notas: real 90 × fórmula sem o +100 60 × a fórmula 25 | ✅ TOMADA (gerente, nota 90 — 🧑 o Founder pode rever, sabendo o risco) | — |
| D-130A1-03 | **"Você economiza até R$ X"** = a mais cara com a mesma cobertura completa − a mais barata mostrada, com a frase dizendo de onde vem a conta; contra o preço ATUAL só com apólice lida. Notas 88 × 75 × sem a origem 30 | ✅ TOMADA (gerente, nota 88) | — |
| D-130A1-04 | **"Corretora Nível 5" é o selo do PROGRAMA**, não de porte: qualquer corretora que entra no canal e cumpre a lista é Nível 5 (config `canal.selo`). A lista do Nível 5 tem de estar ESCRITA e pública (na página do Quem Cobra Menos) antes de abrir ao público — senão é promessa sem critério. Notas: selo com lista 85 × sem lista 45 | ✅ TOMADA (gerente, nota 85) | — |
| D-130A1-05 | **O "mínimo do mínimo" é um 4º cálculo (`minima`)**: a econômica **sem carro reserva** (📊 `carroReserva: 0` pedido ↔ "Não contratar" em 90 de 90 ofertas, 13 seguradoras — cruzado pela F3; "Não"/"Não desejo contratar" vêm de pedidos com código 2: produtos sem carro reserva), vidros básicos (sem vidros a Allianz recusa), terceiros intactos (RCF 0 → recusas), comissão NORMAL. Franquia majorada fica fora até medir o rótulo. Só o canal pede; nunca é a recomendada e sempre diz o que deixa de cobrir. Notas 86 × franquia sem medir 35 × sem o 4º cálculo 50 | ✅ TOMADA (gerente, nota 86) | D-MC-69 (para o canal) |
| D-130A1-06 | **A mensagem do canal termina com UMA pergunta; sem resposta, até 2 lembretes** (💭 15 min e no dia seguinte, em horário comercial — config `canal.follow_up`); quem envia é a 133-A. Notas 88 × só pergunta 72 × lembretes sem pergunta 55 | ✅ TOMADA (gerente, nota 88) | D-MC-71 (para o canal) |
| D-130A1-07 | **O manual de negociação ganha CONTEXTO:** `carteira` (quem já é cliente) e `canal` (consumidor frio do Quem Cobra Menos: prova e vencedor primeiro, a corretora como "quem atende"). A régua de margem é a mesma. Notas 90 × um manual só 55 | ✅ TOMADA (gerente, nota 90) | — |
| D-130A1-08 | **A página do Quem Cobra Menos é OUTRA página, com a marca do Quem Cobra Menos** (o "Q" azul-marinho com a cauda verde-limão), a corretora vencedora DENTRO dela (como um hotel dentro do Booking) e o bloco "Corretora Nível 5". A página da carteira (130-A) fica como está, sóbria, sem nenhuma menção ao Quem Cobra Menos. Entra como fatia PARALELA da 133-A (arquivos disjuntos da conversa), antes dos 5 testadores. Notas: fatia da 133-A 84 × SPEC depois dos testadores 70 × agora, antes da 133-A 60 (o Founder disse "agora só a mensagem") | ✅ TOMADA (gerente, nota 84) | D-130A-11 (só para o canal) |
| D-130A1-09 | **O QR do número do Quem Cobra Menos se lê no PORTAL ADMIN**, numa página "Canais → Quem Cobra Menos → WhatsApp" que reusa o hub de WhatsApp que as corretoras já usam, apontado para a empresa do canal (`platform_canal`) — nunca dentro de uma corretora, nunca no dashboard. Notas: admin reusando o hub 90 × entrar no dashboard como o canal 60 × um app novo do QCM 40 (motor paralelo, CLAUDE.md §5) | ✅ TOMADA (gerente, nota 90) | D-MC-26/58 |
| D-130A1-10 | **O número temporário do canal é o 47 98808-7463** (o WhatsApp Business de teste do Founder) até o definitivo. ⚠️ Ele é HOJE o "cliente de teste" da allowlist do atendimento (`ATTENDANT_INBOUND_ALLOWLIST`): o agente do canal só responde a números CONVIDADOS e nunca a um número de corretora/agente (senão os agentes conversam entre si). Notas: usar já, com as duas travas 82 × esperar o chip 65 | ✅ TOMADA (Founder 06/10 + travas do gerente) | D-MC-52 (temporário) |
| D-130A1-12 | **A trava de produto na régua:** nenhuma corretora configura piso abaixo do piso do produto (10 %) nem um passo que pule a negociação (passo entre 0,5 pp e entrada − autônomo); valor fora vira o padrão com log. Sem humano no laço (D-MC-68 corrigida), um erro de config chegaria direto ao consumidor. Fecha a P-130A-09. Notas 88 × aceitar qualquer piso 30 | ✅ TOMADA (gerente, nota 88) | P-130A-09 |
| D-130A1-13 | ⚠️ **A frase da alavanca de fechamento** ("falei com a seguradora e consegui R$ X a menos") é a pedida pelo Founder; o preço novo sai mesmo do recálculo na seguradora, mas quem cede é a margem da corretora. Fica como está, em R$, sem "%" e sem "comissão"; registrado o risco de o cliente entender que foi a seguradora quem deu o desconto. 🧑 O Founder pode trocar por "consegui uma condição melhor: R$ X a menos" (nota 85, sem a atribuição) | ✅ TOMADA (Founder; risco registrado pelo gerente) | — |
| D-130A1-14 | **A linha "Tempo" da mensagem do canal só aparece até um teto da config** (`canal.tempo_exibido_ate_s`, 💭 90 s); acima, ela SOME — nunca um tempo menor que o medido. 📊 Canário real 07/10: 1º preço aos 284 s, último aos 495 s ("8 min 15 s"): 85 s de fila até o robô disparar e as 2 corretoras em SÉRIE (o `portal-worker` está com concorrência 1). A promessa "cotações em segundos" depende da 133-A baixar a fila e rodar as corretoras em paralelo (P-130A1-08). Notas: esconder acima do teto 85 × mostrar sempre 50 × mostrar só o tempo das seguradoras 70 (ainda 3+ min) | ✅ TOMADA (gerente, nota 85) | — |
| D-130A1-15 | **O Founder REVÊ a D-130A1-02/03/14 para os TESTES CONTROLADOS do piloto fechado (07/10):** *"eu sou o dono do sistema… são testes temporários com o meu círculo social para sentir o que converte; depois ajusto e sigo as regras oficiais"*. (1) "Cotações" = `canal.volume.base` (100) + as cotações FEITAS (preços + tentativas com erro/recusa/sem resposta); (2) **nunca** o número de corretoras ("tiro no pé") — "Corretoras de Nível 5"; (3) seguradoras = todas as CONSULTADAS; (4) economia = o seguro ATUAL do cliente (apólice ou o valor que ele disser na conversa) − o MENOR preço de todos; sem o atual, o maior − o menor; sem parêntese; (5) a parcela em destaque: o menor valor em negrito, "12x" discreto, o preço cheio só mais abaixo; (6) a copy: "Prontinho, Mariana! Descobrimos Quem Cobra Menos no Seguro do seu Compass / Fiz 182 Cotações entre Corretoras de Nível 5 e 14 Seguradoras em 1,5 minutos." O tempo continua o REAL medido, no formato dele, até o teto da config. ⚠️ Risco registrado uma vez (CDC art. 37 ao abrir ao público): a base 100 é CONFIGURAÇÃO e se desliga com um valor | ✅ TOMADA (Founder, 07/10/2026) | D-130A1-02 · D-130A1-03 · D-130A1-14 (no piloto) |
| D-130A1-16 | **Marca da AutoFleet:** sem Instagram; fundada em 2011; o logo enviado pelo Founder entra pelo mesmo armazenamento de marca, e a tela ganha "Ano de fundação" e "Trocar o logo" (não existiam) | ✅ TOMADA (Founder, 07/10/2026) | P-130A1-09 |
| D-133A-13 | **O "Quero fechar" da página do canal volta à CONVERSA do Quem Cobra Menos** (o número do canal), nunca ao WhatsApp da corretora; a passagem à corretora acontece na conversa. Notas 85 × WhatsApp da corretora 70 (e a AutoFleet não tem) | ✅ TOMADA (gerente, nota 85) | — |
| D-133A-14 | **Garagem e uso não são perguntados no piloto**: os códigos do Agger não foram medidos (P-129B-05); o padrão da tela é ASSUMIDO e declarado no pedido. Estado civil: o código mais frequente nas gravações, declarado como assumido. Notas: assumir e declarar 80 × perguntar sem conseguir usar 20 | ✅ TOMADA (gerente, nota 80) | D-MC-59 (no piloto) |
| D-133A-15 | **Lembretes só de segunda a sábado**, no horário comercial da config; domingo empurra para segunda | ✅ TOMADA (gerente, nota 80) | D-130A1-06 |
| D-133A-16 | **A passagem registra evento + card no Inbox do operador** e dá à pessoa o wa.me da corretora vencedora (ou "a corretora vai te chamar"): 📊 07/10 nenhuma corretora aderida tem destino de aviso (grupo de suporte/WhatsApp de marca). Notas 82 × só o grupo 55 × aprovações 40 | ✅ TOMADA (gerente, nota 82) | — |
| D-133A1-01 | **QCM, Cotação e Renovação têm regras e apresentação SEPARADAS** (manual/config por serviço); ajustar uma não muda as outras, salvo ordem explícita do Founder | ✅ TOMADA (Founder, 10/10/2026) | — |
| D-133A1-02 | **"Homem ou mulher?" só para nome ambíguo:** o sexo sai do primeiro nome pela tabela do IBGE (Censo 2010) quando ≥ 70 % de um lado (`canal.sexo_pelo_nome_min_pct`), declarado como assumido no pedido | ✅ TOMADA (Founder 10/10 + gerente, nota 88) | — |
| D-133A1-03 | **Revê a D-129B-11:** com logins DEDICADOS de robô (cotador@), o Agger da corretora entra pela TELA de conexões (cofre, o mesmo serviço do comando); login de PESSOA continua proibido para o robô; um login nunca em duas contas | ✅ TOMADA (Founder 10/10 + gerente, nota 85) | D-129B-11 |
| D-133A1-04 | **O Agger da corretora pela tela é a conta GLOBAL** (QCM e quem não tem Agger próprio); uma só por corretora até a SPEC-131-0 (D-131-0-04: o motor trata todas as contas Agger da corretora como um rodízio) | ✅ TOMADA (gerente, nota 92) | — |
| D-133A1-05 | **A SPEC-131-0 (contas, comerciais, Aggers, sistemas de gestão, WhatsApps por usuário, calcular × negociar) é PLANEJADA agora** (`specs-propostas/SPEC-131-0-CONTAS-COMERCIAIS-E-CONEXOES.md`) e executada antes da 131; fila: 133-A.1 → 129-C → 131-0 parte A → 130-B → 131 → 132 → 133-B → 135 | ✅ TOMADA (gerente, nota 90) | — |
| D-133A1-06 | **A 129-C abre num chat NOVO** (este chegou ao teto de contexto do CLAUDE.md §9); os manuais da Resulta atualizam depois; a regra +15 % é configuração | ✅ TOMADA (gerente, nota 85) | — |
| D-133A1-07 | **A menor parcela é a que a seguradora traz** — 📊 a Youse só traz 4x (nunca se inventa 12x); quando a seguradora traz 12x, o 12x aparece em destaque | ✅ TOMADA (gerente, medido) | — |
| D-130A1-11 | **Comerciais com WhatsApp e Agger próprios** (cada comercial cota na conta dela, recebe o aviso e depois fala com o cliente): **PLANEJADO, não construído** — `programa-multicalculo/PLANO-COMERCIAIS-E-CONTAS.md`. Entra depois da 131 (o auxiliar de renovação é quem precisa dele primeiro). Notas: planejar agora e construir com a 131 85 × construir já 40 | ✅ TOMADA (gerente, nota 85) | D-MC-24/40 |
