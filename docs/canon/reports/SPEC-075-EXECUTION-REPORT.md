# SPEC-075 — Portal Capability Factory Global

**Relatório de execução** · 16/08/2026 · branch `feat/spec075-portal-capability-factory`

| | |
|---|---|
| Commit base | `7a4ca95` (SPEC-074 + SPEC-076 escrita) |
| Commits | 5 |
| Diff | 24 arquivos · +7.691 / −57 |
| Migrations | 2, ambas expand-only, **não aplicadas** |

---

## 1. O que a SPEC-075 entrega, em uma frase

O Portal Worker deixa de ser um serviço que dois chamadores especializados sabem
usar e passa a ser uma **capacidade do Work OS**: quem quer trabalho diz o
*resultado* que quer, e o registro decide a função, o resolver decide a conta, e
o guard decide se pode.

```
ANTES                                   DEPOIS
──────────────────────────────────      ──────────────────────────────────
o registro sabia (módulo, função)       sabe também O QUE a journey faz
cada chamador montava o job na mão      há UMA ponte que monta
portal_jobs sem origem                  portal_jobs com Work Run e operação
uma tool opaca "execute portal"         três tools estreitas, com efeito
o worker rodava 1 job de cada vez       roda N, um por conta, com lease
"failed" sem saber se houve efeito      retry decidido pela fase do checkpoint
```

---

## 2. A invariante que guiou tudo: **um só de cada coisa**

A SPEC-075 §7 lista 27 invariantes. A mais cara de respeitar foi a primeira:
*um registry*. Era tentador criar `JourneyDefinition` num mapa novo ao lado do
antigo — e teria sido a decisão errada, porque dois registros divergem no
primeiro dia em que alguém acrescenta journey num e esquece o outro.

A saída: **`JourneyDefinition` se comporta como a tupla que o mapa devolvia**.
`__iter__`, `__getitem__` e `__len__` estão implementados, então
`modulo, funcao = JOURNEYS[chave]` continua funcionando byte por byte.

📊 Prova: as 11 suítes que leem o registry passaram **sem uma linha alterada**.

O mesmo raciocínio evitou um segundo vocabulário de efeito. `READ_ONLY`,
`REVERSIBLE_UI` e `MATERIAL_SIDE_EFFECT` vêm de `guardrails`, da SPEC-073 —
duas listas de "o que é material" divergem, e a que estiver errada vai ser a que
decide se um clique acontece.

---

## 3. Referências de fora, sem dependência nova

O Founder pediu para não reinventar a roda. Três desenhos foram emprestados; **zero
bibliotecas** entraram por causa deles.

| De onde | O que foi emprestado | Onde vive |
|---|---|---|
| **Stripe** | chave de idempotência **+ impressão do pedido**: a mesma chave com corpo diferente é **erro**, não repetição | `contracts.IdempotencyRecord.conflita_com` |
| **Temporal** | política de retry como **tabela de falhas não-retentáveis**, não como contador de tentativas | `contracts.politica_de_retry` |
| **Kubernetes Lease** | lock com **dono, prazo e renovação** — não `SETNX` e reza | `portal_worker/leases.py` |
| **Airflow** | `priority` como peso, menor = mais urgente | migration `20260816_02` |

O empréstimo do Stripe é o que fecha um buraco que a idempotência ingênua deixa
aberto: sem a impressão do pedido, um segundo acionamento — outra peça, outro
lado — herdaria em silêncio o resultado do primeiro, e o segurado ouviria *"já
abri"* sobre um pedido que não é o dele.

---

## 4. Os blocos, e o que cada um mudou

### Bloco A — o registro passa a dizer o que cada journey é
14 journeys ganharam `business_operation`, `effect_class`, `requires_account`,
`supports_resume`. Três operações nasceram: `billing.overdue.list` (6 portais),
`portal.login.check` (7), `assistance.glass.request` (1, **material**).

`portais_com_cobranca()` virou derivada de `portais_com_operacao()` e devolve
**exatamente** a mesma lista de 6.

### Bloco B — PortalExecutionGateway
🔴 Nasce em `legacy`. `PORTAL_EXECUTION_GATEWAY_MODE` = `legacy|shadow|on`, e
valor irreconhecível vira `legacy` — variável com erro de digitação não liga
caminho novo em produção.

O contrato de entrada **não tem** `journey`, `module`, `function`, `portal_key`,
`account_id`, `cookie`, `token`, `password` nem `proxy`. Essa ausência é a razão
de o contrato existir.

### Bloco C — três tools estreitas, não uma `portal.execute`

⚠️ **CORREÇÃO de 17/08/2026.** Este parágrafo dizia: *"`portal.execute` aparecia
em um lugar do repositório… não havia linha em `tool_definitions`"*. Estava
certo sobre o **repositório** e **errado sobre o banco**.

📊 Lido no banco vivo em 17/08, na hora de aplicar a migration:
`portal.billing_read`, `portal.policy_read` e `portal.execute` **já existiam**,
com release `1.0.0` publicada, `input_schema = {}` e
`execution_manifest.provider = portal_browser`. São das 9 versões aplicadas sem
arquivo que a `MIGRATIONS-AUTHORITY` §4 registra — nenhum `grep` no repositório
podia achá-las.

O erro de método é o que importa: **eu inferi o estado de produção a partir do
repositório.** A própria `MIGRATIONS-AUTHORITY` abre dizendo que o repo não é a
fonte completa do schema, e eu li o repo como se fosse.

A conclusão do bloco **não muda** — as tools existiam vazias, sem schema e
apontando para o provider antigo, o que é quase o mesmo que não existirem para
quem precisa validar entrada. Mas o caminho mudou: em vez de criar, foi preciso
**publicar a release `1.1.0`** com schema real, porque release publicada é
imutável (SPEC-056). Ver `20260817_01_spec075_tools_de_portal_schemas_reais.sql`.

Uma tool única obriga o modelo a dizer *qual journey* rodar — que a §10.4 proíbe
— e tem um `side_effect_class` só, então autorizar leitura de cobrança passaria a
autorizar abertura de atendimento pago.

O `VERIFY` da migration tem uma consulta que **devolve zero linhas** se algum
schema mencionar `journey|module|function|account_id|cookie|token|password|proxy`.
É a §10.4 escrita em SQL.

### Bloco D — `portal_jobs` deixa de ser órfão
6 colunas NULL-áveis, 3 índices, nada existente tocado. Sem FK para
`work_runs`/`tool_invocations` **de propósito**: a DDL dessas tabelas não está no
repositório, e FK para tabela cuja forma não posso conferir transforma migration
aditiva em incidente.

### Bloco E — a ponte que existia e nunca foi ligada
📊 `bridge.portal.job` só **acompanha** um `portal_job_id`, e nenhum código do
repositório preenche esse campo. A ponte foi construída e nunca ligada, porque
faltava quem criasse o job **com linhagem**.

Nasceu `portal.operation`. A linhagem vem do **runtime**, não do payload — se
viesse do payload, um chamador poderia atribuir o próprio trabalho a outro Work
Run.

### Bloco N — concorrência por conta
🔴 A regra que não afrouxa: **a mesma conta nunca roda duas vezes ao mesmo
tempo**. Cada conta tem sessão de navegador persistida; duas em paralelo se
sobrescrevem e derrubam a corretora do portal — não um job, a corretora.

`run_once` ficou **idêntica** ao baseline (Gate D exige). Quem quer paralelismo
chama `run_lote`. Sem Redis a concorrência cai para 1 sozinha.

### Blocos I, J, L, M, Q, U, V
Factory CLI (audit/matrix/validate/scaffold), replay com detector de PII, score
que **anula** em vez de subtrair, matriz gerada, `/health` com concorrência
**efetiva**, e os dois adapters em sombra.

---

## 5. Os erros que eu cometi, e o que cada um ensinou

**O lease nasceu no contêiner errado.** Eu o pus em
`app/services/portals/leases.py`. O `Dockerfile` do portal-worker copia **só**
`backend/portal_worker` — um lease que importa `app.core.redis` **não existe no
processo que precisa dele**. Teria falhado em produção com todos os testes
verdes: a CLAUDE.md §9.1 outra vez. Movido, com cliente próprio, e `redis>=5.0`
no requirements do worker.

**Escrevi um fallback que não existia.** No `billing_collection` comentei que "o
`except` abaixo repete sem a coluna". Não havia `except`. Se o banco não tivesse
`operation_key`, o insert quebraria e a varredura **inteira** da corretora
pararia — por uma coluna que nem é usada ainda.

**Usei um `logger` que o módulo não tem.** `grep` mostrou que a única referência
no arquivo era a que eu tinha acabado de escrever. O fallback quebraria no exato
momento em que precisasse funcionar.

**Deixei dois blocos sem ligação.** L (score) e I (audit) foram construídos por
agentes diferentes e não se conheciam. Sem a costura, a matriz publicava 14
journeys com score 0 — correto e inútil.

**Um juiz crítico achou dois defeitos no que eu tinha acabado de escrever.**
O primeiro é crítico e é meu: `_bater()` chamava `lease.renovar()` e
**descartava o retorno**. `renovar` devolve `False` quando a lease já não é mais
desta worker — e ignorar isso deixa o job continuar clicando numa sessão que
outro worker já tomou. É a colisão exata que o Bloco N foi escrito para
impedir, agora com dois navegadores sobrescrevendo a mesma sessão. Lease de
120s, job de até 1200s: basta o event loop ficar sem ceder controle por mais que
o TTL.

O segundo é anterior à 075, e a 075 o transforma em perda de dado:
`update({"evidence": ...})` substitui a coluna `jsonb` **inteira**, e o worker
começava em `{}`. Ao terminar, apagava `gateway.linhagem`,
`gateway_fingerprint` e `gateway_sombra`. O estrago seria silencioso e no pior
lugar: o diff de sombra existe para decidir o cutover, e sumiria justamente dos
jobs **concluídos** — os únicos que interessa avaliar. E sem
`gateway_fingerprint`, `IdempotencyRecord.conflita_com` trata como "nunca
conflita" qualquer job já processado, desligando a conferência do Stripe para
todo o histórico.

Os dois consertados, com asserção executável e mutação que prova a detecção.

**E uma mutação me ensinou algo novo:** a M9 não acendeu vermelha na primeira
rodada, ela **pendurou** o teste (exit 124). O bloco construía o gateway sem
relógio injetado, então a mutação caía no `sleep` real de 150s. 🔴 Teste que
pendura é pior que teste que falha: no CI não parece defeito, parece máquina
lenta.

---

## 6. Testes

| Suite | Asserções |
|---|---|
| `test_spec075_contrato_da_factory.py` | **151** |
| SPEC-074 (mantidas) | 243 |
| SPEC-073 (mantidas) | 390 |

### As 12 mutações

| # | Mutação | Vermelhas |
|---|---|---|
| M1 | `classe_mais_forte` rebaixa para read | 6 |
| M2 | conflito de efeito nunca reprova | 5 |
| M3 | modo inválido deixa de virar `legacy` | 2 |
| M4 | retry liberado após efeito **confirmado** | 2 |
| M5 | idempotência deixa de ver corpo diferente | 1 |
| M6 | multi-account escolhe a primeira conta | 3 |
| M7 | conta de outra corretora é aceita | 1 |
| M8 | banco fora do ar vira fail-**open** | 2 |
| M9 | gateway executa mesmo em `legacy`/`shadow` | 6 |
| M10 | heartbeat volta a ignorar a perda de posse | 1 |
| M11 | worker volta a apagar o `evidence` do banco | 2 |
| M12 | job com lease perdida volta para a fila | 2 |
| — | restaurado | **0** |

⚠️ São **12**, não as 30 que a §34 pede. As 18 restantes cobrem caminhos que só
existem com infraestrutura (Redis real, Supabase real, canário live) — ver
[P-201](../PENDENCIAS.md).

### Dois testes migrados, nenhum apagado (CLAUDE.md §9.3)

`test_o_portal_nao_abre_duas_vezes_o_mesmo_pedido` lia uma janela de 700
caracteres depois do literal `insert(`; ao extrair as colunas para uma variável,
a janela passou a olhar o `except`. **Ele falhou, e falhou certo** — avisou que
parou de ver o que dizia ver.

`test_spec073_zero_regressao_portais` comparava `baseline..HEAD` e confundia "a
SPEC-073 não tocou nisto" (verdade permanente) com "ninguém nunca mais tocará"
(que ninguém prometeu). Toda SPEC seguinte reprovaria um teste da 073 — e teste
que reprova por motivo legítimo ensina a equipe a ignorá-lo.

---

## 7. Gates

```
151/0   asserções da SPEC-075
217     suites verdes no backend
 17     vermelhas — as MESMAS pré-existentes no baseline 7a4ca95
  12    mutações dirigidas, 12 detectadas, baseline restaurado
  0     erros no `portal_factory validate`
  0     erros no `portal_factory audit` (19 avisos, dívida visível)
200     /health na árvore do contêiner, com os módulos novos
```

**Gate A** (contrato/registry) ✅ · **Gate B** (Work OS bridge) ✅ ·
**Gate C** (Factory) ✅ · **Gate D** (escala) ⚠️ parcial — o lease foi provado
contra um Redis falso, não contra um real · **Gate E** (zero regressão) ✅ ·
**Gate F** (live proof) ❌ — depende de canário, ver pendências.

---

## 8. O que NÃO foi feito, e por quê

| Item | Por quê |
|---|---|
| Aplicar as 2 migrations | 🧑 exige janela e decisão do Founder; ambas expand-only, com APPLY/VERIFY/ROLLBACK escritos |
| Ligar `PORTAL_EXECUTION_GATEWAY_MODE=on` | a sombra ainda não acumulou diffs; virar antes de comparar é apostar |
| Subir `PORTAL_WORKER_CONCURRENCY` | exige Redis provado no ambiente e as migrations aplicadas |
| Canário live (Gate F) | 🧑 exige portal real e autorização |
| As outras 21 mutações | exigem infraestrutura real |

---

## 9. Declaração

**Nenhum motor paralelo foi criado.** Um registry (enriquecido, não duplicado).
Um Tool Gateway (as tools novas entram nele, não ao lado dele). Um Work Run (o
workflow novo se registra no `_REGISTRO` existente). Um worker (o laço ganhou um
modo, não um irmão). Uma fila (`portal_jobs`; nada de fila Redis). O lease usa
Redis para **lock**, não para fila.

---

## 10. FATO · INFERÊNCIA · RECOMENDAÇÃO

**FATO** — 151 asserções novas verdes; 12 mutações detectadas e restauradas; 216
suites verdes e 17 vermelhas pré-existentes; `validate` 0 erros; a ponte nasce
em `legacy` e foi provada não-executante em `legacy` e `shadow`; nenhum segredo
atravessa o contrato (provado por asserção sobre os campos do dataclass).

**INFERÊNCIA** — a arquitetura *deve* permitir que uma seguradora nova de
cobrança entre sem Tool, Skill ou Auxiliar novos. Isso está provado
**estruturalmente** (a tool é por operação, não por seguradora) mas não foi
exercido: nenhuma seguradora nova foi adicionada nesta SPEC.

**RECOMENDAÇÃO** — a ordem que eu seguiria: (1) aplicar as migrations numa
janela; (2) ligar `shadow` e deixar acumular diffs por alguns dias de cobrança
real; (3) só então `on`, e só para `billing.overdue.list`, que é read-only; (4)
concorrência 2 depois de Redis provado; (5) a operação material fica em `legacy`
até o canário da SPEC-076.
