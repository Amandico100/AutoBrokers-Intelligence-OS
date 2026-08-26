# Relatório de execução — SPEC-090: o atendimento de ontem vira conserto de hoje

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-090-o-atendimento-de-ontem-vira-conserto-de-hoje.md` (v1)
**Branch:** `feat/spec090-o-atendimento-de-ontem-vira-conserto-de-hoje`
**Executor:** Opus 5 (1M) · 26/08/2026
**Commit inicial:** `04ded4c` · **Commit final:** `871298e` + este relatório
**Estado final:** CONCLUÍDA COM RESSALVAS

---

## 🧑 PARA O FOUNDER — uma página

### O que muda

Terça de manhã você abre o chat e escreve **"o que aconteceu ontem?"** — e
recebe quantos atendimentos, quantos travaram, em que telas, quem destravou,
quanto tempo, e **o que a Regina e a Saionara anotaram**.

### 🔴 Quatro coisas que você precisa saber

**1. A premissa central da SPEC estava errada, e isso encurtou o BLOCO A de
horas para minutos.**

A SPEC abre dizendo que *"as três ilhas não se falam"*:

| a SPEC dizia | 📊 eu medi, no mesmo banco, no mesmo dia |
|---|---|
| `session_id` não casa `conversations` | ✅ verdade — **e irrelevante** |
| `session_id` não casa `observed_sessions` | ✅ verdade — **e irrelevante** |
| — | 🔴 casa **`attendance_sessions`: 95 de 95 (100%)** |
| — | 🔴 `(empresa, telefone)` casa `conversations`: **63 de 63 (100%)** |

**A ponte que a SPEC diz faltar já existe.** A SPEC testou contra duas tabelas
que nunca foram o alvo. E o backfill que ela orça como *"o trabalho que domina
as ~4h"* tinha **quatro linhas** de alvo (4 acionamentos em 2.778 runs).

**2. 🔴 O `#nota` da Regina, escrito onde a SPEC mandou, chega ao segurado — e
não há código que impeça.**

📊 [`evolution_inbound.py:847`](../../../backend/app/services/whatsapp/evolution_inbound.py#L847):
`fromMe` é o **eco de uma mensagem que o WhatsApp já entregou**. Quando o
produto fica sabendo, o segurado já leu. O gate ② da SPEC — *"ZERO chance de o
`#nota` chegar ao segurado"* — **não é alcançável nesse caminho.** A SPEC trata
isso como o risco *"se o prefixo escapar uma vez"*; medido, é o comportamento
padrão.

✅ **O que foi entregue cobre os dois caminhos e diz a verdade sobre cada um:**

```
chat do PAINEL   ⛔ o produto INTERCEPTA antes de enviar. Nunca sai.   origem=painel
WhatsApp dela    capturada · ⛔ não pausa a IA · já foi entregue       origem=whatsapp
```

🧑 **Sua decisão, e é de uma frase:** na segunda de manhã, diga às duas para
anotar **no chat do painel**. É o único lugar onde o produto consegue garantir
que a nota não sai. (P-090-A)

**3. Achei mais dois lugares onde "anotar viraria assumir" — a SPEC só viu um.**

```
1. pausar_por_intervencao_humana   (webhook)    a SPEC viu  ✅
2. note_manual_outbound            (webhook)    🔴 a SPEC NÃO viu
3. o auto-claim do painel          (Next.js)    🔴 a SPEC NÃO viu — e é o PIOR
```

O terceiro é o pior porque está exatamente onde eu recomendo que elas escrevam:
o comentário do arquivo diz *"Auto-claim: enviar como humano **pausa a IA** e
marca o dono"*. Escrever `#nota` ali pararia o atendimento.

**4. "O que aconteceu ontem?" devolvia outra resposta — e parecia a certa.**

📊 `periodo="ontem"` caía no `else` e devolvia *"últimas 24h"*. Às 10h de terça
isso é metade de segunda e metade de terça. Você perguntava uma coisa e recebia
outra, **apresentada como se fosse a que você pediu**.

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo. 🔴 Ao contrário: o BLOCO D entrou na ferramenta
      `resumo_atendimentos` que **já existia e já estava no Core**, em vez de
      criar uma segunda com pergunta parecida (§5 · teto de 12 ferramentas).
- [x] Duas migrations novas, aditivas, idempotentes, expand-first, não destrutivas.
- [x] ⛔ **Nenhuma mensagem saiu** · 📊 `platform_sends` 24h: **0**.
- [x] ⛔ **Nenhum agente ligado** · 📊 `agent_role='attendance' AND is_active`: **0 de 4**.
- [x] ⛔ Nenhum portal, nenhuma variável de ambiente tocada, nenhum dado pessoal
      impresso.
- [x] ⛔ `git add -A` **não foi usado** — arquivos por nome (P-247).
- [x] ⛔ Toda restauração de mutação **por cópia**, com sha256 conferido (P-231).

---

## 1. BLOCO 0 — a medição refeita

| a SPEC afirma | 📊 medido em 26/08 | |
|---|---|---|
| `attendance_transcripts` 156.443 | **156.447** | ✅ (tabela viva) |
| com `session_id` 152.300 | **152.304** | ✅ |
| sem `session_id` 4.143 | **4.143** | ✅ exato |
| `conversation_scorecards` 686 | **686** | ✅ exato |
| casa `conversations.id`: 0 | **0** | ✅ e irrelevante |
| casa `observed_sessions.id`: 0 | **0** | ✅ e irrelevante |
| `work_runs` sem coluna de conversa | **50 colunas, nenhuma** | ✅ |
| `company_memories` / `knowledge_candidates` / `capability_gaps` / `demand_clusters` = 0 | **0, 0, 0, 0** | ✅ |
| `knowledge_cards` 18.715 | **18.715** | ✅ |
| eventos de travamento = `[]` | **0** | ✅ falta o piloto |

🔴 **E o que a SPEC não mediu:**

```
session_id casa `attendance_sessions` ......... 95 de 95    100,0%
(empresa, telefone) casa `conversations` ...... 63 de 63    100,0%
attendance_sessions ........................... 12.586 linhas
work_runs `acionamento.seguradora` ............      4      0,1% de 2.778
```

---

## 2. O que cada bloco entregou

### BLOCO A — a chave de junção · `09677ee`

`work_runs + conversation_id`, escrita **no ato** a partir de
`session["mirror_conversation_id"]` — que o `dispatch_mirror` já gravava. A SPEC
acertou em cheio nisso.

🔴 **A FK é COMPOSTA, e esse é o ponto:**

```sql
FOREIGN KEY (conversation_id, company_id)
  REFERENCES conversations (id, company_id)
```

Uma FK simples provaria que a conversa existe, **não que ela é da mesma
corretora**. §7: o backend usa service role e atravessa a RLS inteira — a única
proteção real é o filtro no código, e um filtro é uma linha que alguém esquece
numa refatoração de terça. Agora o isolamento é **constraint do banco**.

⛔ **Mas o código não depende dela para não quebrar:** `_conversa_provada_da_sessao`
confere a corretora antes e, na dúvida, grava NULO. Deixar a FK recusar custaria
o acionamento inteiro — o `INSERT` do run é um só.

⚠️ **E eu errei sobre a janela de tempo.** Descartei-a como sobre-engenharia
para quatro linhas. 📊 Errado: os quatro acionamentos têm **dois candidatos
cada** — a conversa do agente interno (04/07 a 15/07) e a do Espelho (17/08 a
20/08). Só por telefone, os quatro ficam ambíguos e nulos. Com a janela, os
quatro resolvem, e a conversa de julho estava morta havia 34 dias.

### BLOCO B — a trajetória do travamento · `9aa45fc`

🔴 **O gate ③ é o produto:** um travamento que nunca destravou é um segurado que
nunca foi atendido. Três formas entram, e as três com as **mesmas chaves**: o
par completo, o aberto sem fechamento, e o destravado órfão (par partido pela
virada da meia-noite).

📊 **§12.1 aplicado a número calculado:** cada tempo declara a **fonte**.
`payload.segundos_travado` é **MEDIDO** (sai de `travado_desde`); a diferença
entre os `created_at` é **DEDUZIDO** (é a hora em que a linha foi escrita). O
medido vence, e o resumo conta quantos de cada.

### BLOCO C — a anotação da Regina e da Saionara · `06a39ee` + o proxy

Migration `notas_da_atendente` com `company_id` + RLS + FK composta + os dois
CHECKs. O texto chega **mascarado pelo mascarador único da casa**, e a
degradação é **fechada**: sem mascarador, a nota não é gravada.

> ⛔ Nota perdida a Regina reescreve. Placa crua em tabela nova não se desfaz.

⚠️ **Maiúscula conta.** 📊 Teclado de celular capitaliza a primeira letra: ela
digita `#nota` e sai `#Nota`. Com a regra sensível, a anotação vira intervenção —
pausa o robô **e** vai para o segurado. Errar para o lado estrito custa as duas.

### BLOCO D — a pergunta de terça-feira · `3ceb3cb`

Entrou em `operations_summary`, a função da ferramenta `resumo_atendimentos` que
**já estava no Core**. 📊 O Tool Gateway tem teto de 12 ferramentas por execução
e o Core carrega perto disso — uma segunda ferramenta com pergunta parecida
degradaria a escolha do modelo em **toda** conversa.

🔴 **O gate ③ é o teto silencioso**, e a própria SPEC registra o caso em
P-090-03. 📊 E o teto não é escolha do código: **o PostgREST devolve no máximo
1.000 linhas por chamada, com ou sem `.limit()`.** A leitura pagina, e quando não
coube ela **declara** em `truncado` — inclusive quando o banco cai no meio,
porque *"nenhum travamento"* e *"não consegui olhar"* contam histórias
diferentes.

---

## 3. Migrations — aplicadas e verificadas

### `20260826_02_spec090_blocoA_work_runs_conversation_id.sql`

```
V1  conversation_id | uuid | nullable=YES
V2  fk_work_runs_conversation_mesma_corretora | f |
      FOREIGN KEY (conversation_id, company_id) REFERENCES conversations(id, company_id)
    uq_conversations_id_company | u | UNIQUE (id, company_id)
V2b ix_work_runs_conversa (parcial, WHERE conversation_id IS NOT NULL)
V3  🔴 CONTROLE (transação desfeita por `raise`):
      cross-tenant RECUSADO? t | mesma corretora ACEITO? t | fantasma RECUSADA? t
      outros erros: []   ·   0 linhas sobraram
V4  acionamento: 4 total · 4 ligados · 0 nulos · 0 cross-tenant
```

⚠️ **E o CONTROLE já se pagou na primeira rodada:** os três inserts falharam com
`23502` e `23514` — `NOT NULL` em `outcome_title`/`input_fingerprint`/
`idempotency_key`, e o CHECK `ck_work_runs_thread_format`
(`thread_id = 'work:'||company_id||':'||id`). **Nada a ver com a FK.** Sem a
linha de controle, eu teria creditado a recusa ao guarda errado.

### `20260826_03_spec090_blocoC_notas_da_atendente.sql`

```
🔴 OS VALORES DO CHECK, listados no APPLY:
   ck_notas_atendente_origem  CHECK (origem IN ('painel', 'whatsapp'))
   ck_notas_atendente_texto   CHECK (length(btrim(texto)) > 0)

V3 🔴 CONTROLE, AS QUATRO LINHAS (transação desfeita):
   origem inválida RECUSADA? t | texto vazio RECUSADO? t
   cross-tenant RECUSADO?    t | nota VÁLIDA aceita?   t
   outros erros: []
```

---

## 4. Os defeitos — e **todos** foram criados pelos meus próprios consertos

📊 Nove defeitos, e o padrão é um só em cinco deles.

### 🔴 Cinco vezes a mesma coisa: a asserção leu a PROSA, não o código

| # | onde | o que passava sem dever |
|---|---|---|
| 1 | `test_o_escritor_confere_a_corretora` | apagar `.eq("company_id")` — a **docstring** diz a frase |
| 2 | `test_a_migration_tem_FK_COMPOSTA` | `UNIQUE (id, company_id)` → `UNIQUE (id)` — o **VERIFY** repete no comentário |
| 3 | `test_o_painel_INTERCEPTA_ANTES_de_enviar` | apontava o erro **ao contrário** — o comentário cita `send_message` |
| 4 | o aplicador do BLOCO D | *"já aplicado"* sobre a **menção na docstring do módulo** |
| 5 | o guarda da regra única | `split('Auto-claim')` pegou o **cabeçalho do arquivo** |

> ⚠️ Nos cinco, o guarda estava lendo a **explicação de por que o código deveria
> existir**, e concluindo que ele existia. §9.3.

Cada um ganhou um cortador de prosa **com controle que prova que ele corta**.

### 🔴 E quatro defeitos de comportamento

| # | achado | como apareceu |
|---|---|---|
| 6 | 🔴 **a linha órfã nascia com SEIS chaves em vez de doze** — `KeyError` na forma mais rara, a da virada da meia-noite | o próprio guarda, 1ª rodada |
| 7 | 🔴 **a hora ilegível REORDENAVA os eventos** — `"hora invalida"` começa com `h` e vai depois de `"2026-…"`; UM travamento virava DOIS | o próprio guarda, 1ª rodada |
| 8 | 🔴 **`_e_nota` nascia DENTRO do `try`** — literalmente o defeito que o juiz da SPEC-093 achou em `_fomos_nos`, três linhas acima, com o comentário explicando por quê | revisão de olhos frescos |
| 9 | 🔴 **`since` sem `until`** — a janela ficava aberta para a frente e *"ontem"* incluía hoje | `grep` da própria mudança |

⚠️ **E o #9 quebrou um guarda PRÉ-EXISTENTE.** O stub de
`test_spec040_onda2_operational_view` não conhecia `.lte`, então a cadeia
levantava `AttributeError`, o `except` do serviço engolia, e **duas seções
sumiam da saída em silêncio**. O fato mudou, o stub mudou com ele, e a **lição
migrou**: o guarda agora prova que `ontem` traz o de ontem, **não** traz o de
hoje, e que os dois rótulos são diferentes. 📊 **20 → 25 casos, 25 verdes.**

⚠️ E a linha de controle desse guarda **corrigiu uma afirmação minha**: escrevi
que `hoje` não pegaria a atividade de ontem ao meio-dia. Falso — *"hoje"* é
janela **deslizante** de 24h e alcança legitimamente. Quem estava errado era a
asserção, não o código.

---

## 5. Testes — saída real

```
test_a_chave_de_juncao_do_atendimento.py    25 passed
test_a_trajetoria_do_travamento.py          28 passed
test_a_anotacao_da_atendente.py             34 passed
test_a_pergunta_de_terca_feira.py           24 passed
                                            ──────────
                                           111 passed

test_spec040_onda2_operational_view.py      25 passaram, 0 falharam  (era 20)
spec090-a-regra-do-prefixo-e-uma-so.test.mjs 24 passaram, 0 falharam
tsc --noEmit                                 exit 0
```

### As mutações — 89 no total

| bloco | mutações | vermelhas | verdes |
|---|---|---|---|
| A | 17 | **17** | 0 |
| B | 17 | **17** | 0 |
| C | 28 | **28** | 0 |
| D | 22 | **22** | 0 |
| | **84** | **84** | **0** |

🔴 **As obrigatórias da SPEC, todas vermelhas:**

```
A · afrouxar a regra de evidência (só telefone, sem janela)  →  5 testes caem
B · o travamento ABERTO some da trajetória                   →  9 testes caem
C · desligar o consumo do prefixo no painel                  →  vermelha
D · o corte deixa de ser DECLARADO                           →  vermelha
```

⚠️ **Sete mutações ficaram VERDES antes de o número valer**, e cada uma era um
guarda que não guardava:

1. o escritor sem `.eq("company_id")` → a docstring passava
2. a `UNIQUE` composta → o comentário do VERIFY passava
3. o teto de curingas… *(087)* · aqui: **o log imprimindo o texto da nota** — eu
   procurava `{texto` e a mutação escrevia `{linha['texto']}`
4. 🔴 **o banco de mentira IGNORAVA `.limit()`** — com ele ignorado, `count` e
   `len(data)` davam o mesmo número e *"o total vem da PÁGINA"* passava
5. 🔴 **o teste da falha derrubava o banco INTEIRO** e conferia `truncado`
   não-vazio — mas ele já vinha cheio pela seção de atendimentos, e a metade dos
   travamentos passava sem ninguém olhar
6. e duas **mutações VAZIAS minhas**: tirar o `^` do padrão não muda nada
   (`.match` já ancora), e `.match`→`.search` também não (o `^` já ancora). O
   prefixo está protegido **em dobro**; a mutação real precisa remover os dois.

> ⚠️ **Um banco de mentira que não respeita o contrato do de verdade não testa o
> código: testa a mentira.**

---

## 6. 📊 A BATERIA

> Lido de `backend/.diario-da-bateria.jsonl`, que o `conftest.py` escreve.
> 🔴 **Commit não é rodada.**

| | |
|---|---|
| rodadas nesta SPEC | 📊 **283** |
| das quais **bateria inteira** | 📊 **2** |
| relógio total esperando a suíte | 📊 **43.7 min** |
| só as inteiras | 📊 **29.1 min** — **67% do relógio** |

### As inteiras

```
08:08:55 UTC   902.9 s   890 coletados   3 falhas   commit 3ceb3cb
08:24:17 UTC   844.4 s   890 coletados   2 falhas   commit 3ceb3cb
```

📊 **Os guardas cresceram 111** entre o fim da 087 (779) e esta SPEC (890).

### ⚠️ As 3 falhas — nenhuma é desta SPEC

```
test_o_handoff_nao_e_um_buraco      passa SOZINHO: 8 asserções verdes, 0 vermelhas
test_a_arvore_ficou_limpa_no_fim    o vazamento de mutação (P-246), agora em replay.py
test_a_politica_de_autorizacao      só na 1ª rodada — 6/6 em TRÊS rodadas seguidas
                                    depois, e AUSENTE da 2ª bateria inteira
```

🔴 **A primeira e a segunda são a mesma coisa:** um guarda mutou `replay.py`,
estourou o tempo, e a mutação escapou do `finally` dele. O restaurador limpou a
árvore e **se reportou** — e o `test_o_handoff_nao_e_um_buraco` foi a vítima,
lendo rotas de um arquivo mutado. 📊 É a P-246, com outro arquivo.

---

## 7. Pendências abertas

`P-090-A` 🧑 🔴 **onde a Regina e a Saionara escrevem a nota** — a decisão de
uma frase, antes do piloto ·
`P-090-B` 🧑 `internal_numbers` vazio nas três integrações ·
`P-090-C` o teto silencioso das seções **antigas** de `operational_view` ·
`P-090-D` `attendance_sessions` e `observed_sessions` com as **mesmas colunas** —
e a confusão entre elas já custou a premissa central desta SPEC ·
`P-090-E` 🧑 o dia do relatório é **UTC**, e o piloto é UTC−3 ·
`P-090-F` a fila `notas_da_atendente` não tem tela.

E as que a própria SPEC já listava (`P-090-01` a `P-090-05`) continuam de pé.

---

## 8. O que a SPEC previa e não foi feito

⛔ **Nada foi cortado.** As doze peças que a SPEC v1 já tinha tirado da proposta
(event envelope, Episode, scope resolver, garimpo, a *Demand Intelligence*)
continuam fora, com o gatilho de cada uma escrito na SPEC.

⚠️ **E o canário Amandus → Resulta → AutoFleet não foi executado**, pelo mesmo
motivo das SPECs 093 e 087: ele exige ligar o atendimento, e as travas proíbem.
O que deu para verificar sem ligar nada está na §0.

⚠️ **O BLOCO C mudou de desenho em relação ao texto da SPEC** — não de escopo.
O resultado que ela pede (*"a anotação entra no produto, ligada à conversa, sem
pausar o robô, sem chegar ao segurado"*) foi entregue. O que mudou é **onde** a
garantia é possível, e a razão está medida na P-090-A. Registrado também em
`CHANGE-ADDENDA` como **ESSENCIAL**.

---

## 9. Separando FATO de INFERÊNCIA

**📊 FATO** — medido, com fonte:

- `session_id` casa `attendance_sessions` em 95/95 (100%); `(empresa, telefone)`
  casa `conversations` em 63/63.
- `acionamento.seguradora` são 4 de 2.778 runs; os 4 foram ligados, 0 nulos.
- `fromMe` devolve `skip=True` — o produto não é o remetente.
- `periodo="ontem"` devolvia *"últimas 24h"*.
- O Core carrega perto do teto de 12 ferramentas.
- 1ª rodada: **842 passed, 3 failed** (902,9 s) · 2ª: **843 passed, 2 failed**
  (844,4 s). A 3ª falha da 1ª rodada era a instabilidade do `node` — 📊 o mesmo
  arquivo deu **6/6 em três rodadas seguidas** logo depois.

**💭 INFERÊNCIA** — não medido, e marcado:

- 💭 Que a Regina e a Saionara vão preferir o painel ao WhatsApp para anotar.
  **Não foi testado com elas.**
- 💭 Que 20 páginas (20.000 eventos) é folga suficiente para um dia de piloto.
  Baseado em 4 acionamentos históricos — o piloto pode desmentir na primeira
  semana, e o `truncado` é quem vai avisar.

**🔴 RECOMENDAÇÃO:**

1. 🧑 Dizer às duas, na segunda de manhã, **anotem no chat do painel** (P-090-A).
2. Na terça, perguntar *"o que aconteceu ontem?"* no chat — e conferir o número
   contra o banco antes de confiar nele pela segunda vez.
3. Se aparecer `⚠️ RESPOSTA INCOMPLETA`, **é o `truncado` funcionando**, não um
   erro: aumente `_PAGINAS_MAXIMAS` ou reduza a janela.
