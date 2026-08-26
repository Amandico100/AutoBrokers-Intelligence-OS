# Relatório de execução — SPEC-093: o atendimento real liga e funciona

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-093-o-atendimento-real-liga-e-funciona.md` (v3)
**Branch:** `feat/spec093-o-atendimento-real-liga-e-funciona`
**Pasta de trabalho:** `AutoBrokers-FIX`
**Executor:** Opus 5 (1M) · sessão de 25–26/08/2026
**Commit inicial:** `e760b0c`
**Commit final:** `<preenchido no commit do relatório>`
**Estado final:** CONCLUÍDA COM RESSALVAS

---

## 🧑 PARA O FOUNDER — o que você precisa saber, em uma página

### O que está pronto e LIGADO

Nada muda sozinho. Todo o código desta SPEC está no lugar e **inerte** até você
apertar um botão. 📊 Zero mensagens saíram; os quatro agentes de atendimento
continuam desligados.

### O que muda quando você apertar

| você faz | o produto faz |
|---|---|
| dá o papel `attendant` a alguém | ela liga/desliga o atendimento — **e nada mais** |
| liga o atendimento (como admin) | os **14 corredores** ligam junto, respeitando o que você pausou à mão |
| liga o atendimento | a tela recebe a **prévia** de quem seria saudado — e **não manda nada** |
| a atendente responde a seguradora pelo WhatsApp dela | o produto **passa a saber** que foi ela, e não o robô |

### 🔴 As três coisas que preciso que você decida

1. **A saudação está pronta e sem tela** (P-258). O caminho existe ponta a ponta;
   falta a tela que mostra a prévia e tem o botão de confirmar. 📊 **25 pessoas**
   escreveram nas últimas 24h e não foram respondidas — são elas que a saudação
   alcança. Outras **214** escreveram há mais de um dia e **não recebem nada**,
   por decisão: acima de 24h a Meta exige template e a saudação vira exumação.

2. **A SPEC pedia um valor que o banco recusa.** Ela escrevia
   `unblock_state='destravado_por_humano'`; 📊 o CHECK só aceita cinco valores, e
   esse não é um deles — e o botão *arquivar* filtra por dois deles, então o caso
   **sumiria da Fila**. Usei `assumido_por_humano`, que é o mesmo ato pelo outro
   canal e o que o painel já escreve. **Se você quis outra coisa, o bloco volta.**

3. **`INSURER_DISPATCH_LIVE` continua fora do ambiente** (P-168). Enquanto
   estiver assim, o piloto não fala com seguradora de verdade — e o Sentinela,
   que 📊 envia sem consultar esse portão (P-250), não morde. **Não é trava: é
   sorte.**

### O que me custou o dia, e por quê

Escrevi seis blocos, todos com gate verde. Depois um painel de **4 lentes
cegas** achou **22 defeitos — 6 deles graves, e todos os 6 criados pelos meus
próprios consertos**. O pior invertia o bloco inteiro: o eco da voz do robô
passaria a ser gravado como *"uma pessoa da corretora assumiu este caso"*.

Consertei, e um **juiz novo** disse **STALLED** — o meu conserto do painel tinha
criado outro. Consertei de novo.

> 🔴 **Nenhum desses oito seria encontrado relendo o código.** Vieram de medir,
> de rodar a bateria inteira, e de olhos que não escreveram o conserto.

⚠️ E a bateria terminou com **dois vermelhos que não são desta SPEC**: é o
vazamento de mutação da P-246, que morde desde 22/08. Estreitei a causa e fechei
a metade que dava para fechar — ver §8.1.

---

## 0. Declaração de integridade

- [x] **Nenhum motor paralelo foi criado.** Ao contrário: o BLOCO D **recusou**
      construir limitador próprio e passou a sair por `platform_outbound`; o
      BLOCO G **fundiu** a âncora singular na plural; e o escritor morto
      `marcar_desligamento` foi **removido** por ter um irmão vivo no TypeScript.
- [x] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada.
      Uma migration **nova** foi criada e aplicada: aditiva, idempotente,
      expand-first, não destrutiva.
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo aparece em log, artifact ou neste relatório.
- [x] ⛔ **Nenhuma mensagem saiu.** 📊 `platform_sends` nas últimas 24h: **0**.
- [x] ⛔ **Nenhum agente foi ligado.** 📊 `agents` com `agent_role='attendance'`:
      **4 linhas, `is_active=true` em 0**.
- [x] ⛔ Nenhum portal de seguradora foi acessado.
- [x] ⛔ Nenhuma variável de ambiente de produção foi tocada.
- [x] ⛔ Nenhum CPF, telefone, apólice, placa ou nome de pessoa foi impresso.
- [x] ⛔ **`git add -A` não foi usado uma única vez** — todo commit adiciona
      arquivos por nome (P-247).

---

## 1. Resumo executivo

Sete blocos, na ordem que a SPEC mandou: **E → A → B → C → D → G → F**.

**O que o corretor ganha:**

- a **atendente** liga e desliga o atendimento **sem receber a configuração
  inteira junto** — o portão é por campo, não por papel;
- o **cliente real deixa de ser descartado em silêncio**: a allowlist conta o
  que barra, e o `/health` mostra;
- o **clique dela para de ser creditado ao robô**. Coluna, linha do tempo e
  canal. E o travamento virou **evento contável**, com rota e tela;
- ao **religar**, o agente **saúda e pergunta** — governado pelo limitador que
  já existia, com prévia obrigatória antes do primeiro envio;
- **um clique liga os 14 corredores**, e o que ela pausou à mão **fica pausado**.

**Três defeitos foram encontrados MEDINDO, e nenhum estava na SPEC:**

1. 🔴 o painel escrevia `actor_type: 'human'` em `work_events`, e o CHECK do
   banco só aceita seis valores — `human` não é um deles. **A linha do tempo do
   botão "assumir" morria no primeiro clique.** 📊 0 linhas com ator humano em
   27.985 eventos;
2. 🔴 a SPEC pedia `unblock_state='destravado_por_humano'` — valor que o CHECK
   recusa, e que faria o caso **sumir da Fila** (o `arquivar` filtra
   `.in(['travado','assumido_por_humano'])`);
3. 🔴 a minha própria anti-duplicata pedia `.limit(5000)` de uma API que entrega
   **1000**. Corretora com mais de mil saudações saudaria gente repetida.

**E o painel de 4 lentes cegas achou 22 defeitos, 6 deles blockers — todos os 6
criados pelos próprios consertos desta sessão.** O mais grave inverteu o BLOCO C:
o eco da própria voz do robô passaria a ser gravado como *"uma pessoa da
corretora assumiu este caso"*.

---

## 0.1 Telemetria (PROTOCOLO §11)

| | |
|---|---|
| linhas de código de **produto** | 📊 **~1.560** |
| linhas de **guarda** (pytest + `.test.mjs`) | 📊 **~2.900** |
| razão guarda/produto | 📊 **~1,9×** |
| linhas de documento canônico | 📊 **~450** (`FOUNDER-DECISIONS` + `PENDENCIAS`) |
| rodadas do painel | **1** |
| lentes | **4**, cegas entre si, **proibidas de rodar pytest** |
| achados do painel | **22** · 6 blockers · 16 pendências |
| **blockers criados pelos próprios consertos** | 🔴 **6 de 6** |
| juiz de confirmação | **1**, novo, sem ter visto o código |
| veredito do juiz | 🔴 **STALLED** — 1 blocker novo, criado pelos consertos do painel |
| achados do juiz | 1 blocker · 2 pendências · 1 guarda-que-não-guarda |

### O laço (§6)

| unidade | voltas | por que a volta a mais |
|---|:---:|---|
| BLOCO C | 3 | a mutação obrigatória **não ficou vermelha**; depois o painel achou a inversão do eco |
| BLOCO D | 3 | a **bateria inteira** achou o `.limit(5000)`; depois o painel achou o N+1 e o dublê permissivo |
| BLOCO G | 3 | uma das 7 mutações ficou **verde**; depois o painel achou a autorização vazando |
| BLOCO A | 2 | o painel achou que **nada executava a rota** |

🔴 **E o juiz de confirmação disse STALLED.** O que ele achou era meu, e era do
**cruzamento** dos consertos do painel:

📊 `assumido_por_humano` é **grudento** — a escrita de `travado` filtra por
`IS NULL`, a de `retomado_pelo_robo` por `== 'travado'`. Nenhuma escrita
posterior o tira. Meu conserto lia essa coluna para creditar o humano no
destrave pelo painel, e o preço era **todo destrave seguinte daquele run virar
trabalho de pessoa** — a mesma mentira do eco da própria voz, com o gatilho
invertido. E `session = dict(session)` rebindava o nome local: as escritas do
rodapé caíam na cópia, e `travado_desde` nunca mais persistia.

**A escolha foi conservadora e está registrada (P-259):** a injeção saiu. O
destrave pelo painel sai `por: robo` — erro na direção segura, num caminho que
📊 não tem nenhum consumidor de UI — em vez de uma mentira que atravessa a vida
inteira do run.

O juiz também apontou **um guarda que não guardava**:
`ativarTodosOsCorredores` não era **executada** por teste nenhum, e a mutação
`sem_ancora: 0` passava a suíte verde. → `spec093-corredores.test.mjs` ganhou
**14 asserções de IO**, com dublê de Supabase, `console.error` capturado e dois
tenants. As quatro mutações que ele escreveu ficam vermelhas agora.

---

## 2. Escopo executado por bloco

### BLOCO E — a decisão do finalize (registro) · `b2a2537`

`FOUNDER-DECISIONS.md`, **D-093**, com a premissa **medida**:

```
sessões com confirmação da seguradora ........... 128
sessões em que a palavra "cancelar" aparece ......  86
as duas coisas na mesma sessão ...................  56
🔴 cancelamentos DEPOIS da confirmação ...........  12
   mais rápido 0,0 min · mediana 34,3 min · mais lento 103,5 min
   abaixo de 5 min: 5 de 12 (42%) · allianz, porto, tokio
```

⚠️ E o registro diz, por escrito, **o que esse número não é**: eu medi *quando
uma pessoa cancelou*, não *quando ficou tarde demais*. São perguntas diferentes,
e tratá-las como a mesma seria o defeito da §12.1.

### BLOCO A — a atendente aperta o botão, e só o botão · `e373dc1`

📊 `company_members`: 8 `admin_company` + 2 `member`. O botão exigia
`TENANT_WRITE_ROLES` → `member` recebia 403; e dar `admin_company` abriria
prompt, integrações e billing junto.

Papel `attendant`, com **portão por campo**. ✅ **Sem migration:** 📊
`company_members.role` é `character varying` sem CHECK e sem enum.

🔴 **E o gate ganhou executor.** 📊 `scripts/admin-auth-policy.test.mjs` existia
desde a TA2-B e **ninguém o rodava**. Agora um pytest o lança por subprocesso, e
prova que o lançador enxerga vermelho.

⚠️ **O painel achou o buraco maior:** a autorização mudou de
`requireCompanyMember({write:true})` para um `if` dentro da rota, e **nada
executava a rota**. A mutação `if (false && !decisao.permitido)` deixava 47
gates verdes — e qualquer `member` escrevia o prompt do agente.
→ `scripts/spec093-a-rota-do-botao.test.mjs`, **27 asserções, rota real**.

### BLOCO B — o descarte deixa de ser mudo · `25d43c2`

O item 1 **saiu porque já estava feito** — provado executando a função real.

- **contador de descarte** (conta, e só; nunca o telefone);
- **`/health`** com `allowlist_ativa`, `allowlist_tamanho`, `allowlist_descartes`;
- 🔴 **o alarme de deriva ganhou destino próprio** — `route_sentinel` montava o
  destino do alerta com a **allowlist de entrada**, e esvaziá-la (o objetivo do
  bloco) devolvia `""`: alerta para ninguém. 📊 14 linhas de `route_drift` de
  25/08, todas `structural`/`escalated`.

### BLOCO C — o travamento vira evidência · `43b92fb`

📊 `assumido_por_humano` = **0** · ator humano em `work_events` = **0** de
27.985 · `work_steps` com marca `manual` = **0**.

- **C.1** o clique vira três escritas: marca na sessão, `unblock_state` **só onde
  está `travado`**, e a linha do tempo com o canal;
- **C.2** **um evento por travamento, não um estado por run** — e os eventos saem
  **mesmo quando a coluna não muda**;
- **C.3** Cérebro e Sentinela deixam rastro.

🔴 **Os dois blockers que o painel achou aqui, e as duas lentes concordaram:**

1. `note_manual_outbound` roda para **todo** `fromMe` — inclusive o eco da voz
   do próprio robô. Com as escritas duráveis, uma URA de 15 turnos escreveria
   ~15 linhas dizendo que **uma pessoa** trabalhou onde só o robô falou. O
   guarda `e_a_nossa_propria_voz` existia desde 06/08 e já era calculado no
   webhook — **só faltava ser usado**;
2. `destravado_por` era limpo só no destrave: uma marca posta **fora** de
   qualquer travamento sobrevivia e era consumida pelo travamento seguinte.

E **um erro meu de máquina de estados**, exposto pelo conserto do filtro:
Cérebro e Sentinela **são** o robô para efeito da coluna. Tratá-los como
"não-robô" deixava `unblock_state='travado'` **para sempre** depois de um
destrave automático. Quem distingue qual robô trabalhou é o **evento** — é o
C.2 inteiro.

### BLOCO D — ao religar, saúda e pergunta · `b26ac72`

📊 O robô teve **4 conversas de WhatsApp em toda a história do produto**.

📊 **E quem o bloco realmente alcança** (medido em 26/08/2026, query em P-258):

```
elegíveis (≤24h, sem dono, sem handoff, sem resposta) ....   25
sem resposta há MAIS de 24h ..............................  214   ← não recebem
```

⚠️ **214 pessoas escreveram e não foram respondidas há mais de um dia**, e o
BLOCO D **não fala com elas** — por decisão, e o motivo está no código: acima de
24h a janela da Meta exige template, e a saudação vira exumação. Elas continuam
na tela de Conversas. 🔴 O bloco entrega 25 conversas recuperáveis, não 239.

- `agents.desligado_em` (📊 `updated_at` não serve);
- ≤12h / 12–24h / **>24h nunca** (📊 acima disso a Meta exige template, e 181 das
  234 têm mais de 7 dias);
- ⛔ **nenhum limitador novo**: `send_to_client_guarded(FRIA)`;
- idempotência **pela mensagem, não pelo clique**;
- prévia obrigatória; prévia é `GET`, envio é `POST`, `confirmado` vem do corpo.

**O que o painel e a bateria acharam aqui:**

| | |
|---|---|
| 🔴 `.limit(5000)` de uma API que entrega 1000 | **a bateria inteira**, 40 min depois de eu escrever |
| 🔴 N+1: 1 + 86 queries sequenciais, e varredura **dupla** (~174 idas) | lente 4 |
| 🔴 o dublê ignorava `.order(desc)` e `.limit()` | lente 3 |
| 🔴 o ramo do UNIQUE tinha **cobertura zero** | lente 3 |
| `_reservar` confundia duplicata com erro | lente 1 |
| `marcar_desligamento` sem chamador (irmão vivo no TS) | lente 1 |
| o BLOCO D **não tinha gatilho nenhum** | lentes 3 e 4 |

→ O religamento passou a devolver a **prévia** na resposta do botão. ⛔ Sem
enviar nada.

### BLOCO G — um clique liga os 14 · `4804a98`

🔴 **A decisão do G.2 foi minha, e foi LOTEAR.** 📊 `ensureCorridorAnchor` fazia
`SELECT + INSERT` por corredor, e `corridor_templates` tem 2 linhas, ambas
`scope='global'` com `company_id` NULO, enquanto a busca filtrava
`.eq('company_id', companyId)` — **42 idas sequenciais**. Virou 3.

⚠️ E lotear torna a **retomabilidade mais fácil** de provar: três passos, cada um
idempotente sozinho. Cair entre eles deixa âncoras órfãs — que é exatamente o
estado de quem nunca clicou.

🔴 **O painel achou que este bloco desfazia o BLOCO A:** o toggle disparava
`ativarTodosOsCorredores`, que escreve configuração — e a rota dedicada a essa
escrita exige `write: true`. O papel `attendant`, criado para **não** abrir a
configuração, instalaria 14 corredores em nome da corretora.
→ Agora quem liga os corredores é **quem já podia ligá-los à mão**. O clique da
atendente liga o atendimento, e só.

### BLOCO F — a prova

§§ 4, 5 e 6 deste relatório.

---

## 3. Migration

### `20260825_01_spec093_blocoD_saudacao_do_religamento.sql`

**APPLY** — aplicada em produção (`dcajcvlzcjbmyapmklil`) em 25/08/2026.
`agents.desligado_em timestamptz` + `saudacoes_enviadas` com UNIQUE nas três
colunas de chave, duas FKs `ON DELETE CASCADE`, dois índices, RLS ligada sem
policy (mesma escolha das 14 tabelas da SPEC-059).

**VERIFY** — saída real:

```
V1 coluna     desligado_em / timestamp with time zone / null=YES
V2 rls        saudacoes_enviadas / rls=true / policies=0
V3 índice     uq_saudacoes_enviadas_chave UNIQUE
              (company_id, conversation_id, inbound_message_id)
              ix_saudacoes_enviadas_empresa (company_id, enviada_em DESC)
V4 fk         saudacoes_enviadas_company_id_fkey      ON DELETE CASCADE
              saudacoes_enviadas_conversation_id_fkey ON DELETE CASCADE
V5 🔴 CONTROLE  o UNIQUE recusou a segunda linha?  t
                (em transação desfeita por `raise` — 0 linhas restantes)
```

**ROLLBACK** — escrito **antes** de aplicar, no próprio arquivo. Destrutivo por
natureza: só com decisão explícita do Founder (`CLAUDE.md` §8, proibição 6).

---

## 4. O gate do BLOCO F

| | prova |
|---|---|
| ① gates de A, B, C, D, G passam | §5 |
| ② 🔴 os quatro `attendance` continuam `is_active=false` | 📊 `SELECT`: **4 agentes, `is_active=true`: 0** |
| ③ 🔴 zero mensagens enviadas | 📊 `platform_sends` nas últimas 24h: **0** · `saudacoes_enviadas`: **0** |
| ④ a decisão do BLOCO E está escrita | `FOUNDER-DECISIONS.md`, D-093, commit `b2a2537` |
| ⑤ bateria inteira verde, com o número de rodadas | §6 |
| ⑥ dois tenants em cada bloco | gates ⑦ (C), ⑧ (D), ⑥ (G) — **todos com linha de controle** provando que a outra corretora *consegue* aparecer |

### A mutação obrigatória de cada bloco — saída real

```
BLOCO B    destino próprio some + descarte volta a ser mudo   → 4 vermelhos
BLOCO C 🔴 desligue a marca do humano                          → 1 vermelho, no GATE ③
           (⚠️ a 1ª versão do gate ③ ficou VERDE: marcava a sessão à mão e
            nunca passava por `note_manual_outbound`. Reescrito.)
BLOCO D    9 mutações, uma por fator, com CONTROLE             → 9 vermelhos
BLOCO G 🔴 desligue a checagem do ②                            → 1 vermelho
           (⚠️ "a âncora volta a ser um-a-um" ficou VERDE na 1ª rodada:
            o guarda procurava a chamada, a mutação mexia no RETORNO.)
ROTA    🔴 a mutação que a lente 3 escreveu                    → 6 vermelhos
           (antes do gate novo, ela deixava 47 asserções verdes)
```

Toda restauração **por cópia**, com sha256 conferido dos dois lados (P-231).

---

## 5. Testes — saída real

```
scripts/admin-auth-policy.test.mjs        47 passaram, 0 falharam
scripts/spec093-toggle.test.mjs           19 passaram, 0 falharam
scripts/spec093-corredores.test.mjs       44 passaram, 0 falharam   ← + IO real
scripts/spec093-a-rota-do-botao.test.mjs  27 passaram, 0 falharam   ← rota REAL
                                         ───────────────────────
                                          137 asserções em `node`
npx tsc --noEmit                          exit 0
```

### As mutações do JUIZ — todas vermelhas depois do conserto

```
CONTROLE (sem mutação) ..................... 44 passaram, 0 falharam
🔴 `sem_ancora: lote.semAncora.length` → `0`  43 passaram, 1 falharam
   o `console.error` do store some ......... 43 passaram, 1 falharam
   o insert das âncoras vira no-op ......... 36 passaram, 8 falharam
   o filtro por corretora some da leitura .. 42 passaram, 2 falharam
restaurado por cópia, sha256 idêntico ...... 488f918fe5dbec27
VERDE DE NOVO .............................. 44 passaram, 0 falharam
```

⚠️ As duas do meio ficavam **verdes** na primeira rodada: o teste não capturava
`console.error`, e o fixture tinha uma corretora só. §9.3 — as duas foram
consertadas antes de o número acima valer.

Guardas pytest desta SPEC:

```
test_a_atendente_aperta_o_botao_e_so_o_botao.py    6 passed
test_o_cliente_real_nao_e_descartado.py           12 passed
test_o_travamento_vira_evidencia.py               34 passed
test_a_saudacao_do_religamento.py                 47 passed
test_um_clique_liga_os_corredores.py               8 passed
```

**Bateria inteira:** ver §6.

---

## 6. 📊 A BATERIA — quantas vezes ela rodou nesta SPEC

> 🔴 Obrigatório (`PROTOCOLO-AUTOBROKERS-AAA.md` §10). **Commit não é rodada.**
> Lido de `backend/.diario-da-bateria.jsonl`, que o `conftest.py` escreve.

| | |
|---|---|
| rodadas no total, nesta SPEC | 📊 **100** |
| das quais **bateria inteira** | 📊 **4** |
| relógio total esperando a suíte | 📊 **~57 min** |
| só as inteiras | 📊 **~53 min** |
| fração do relógio que é bateria inteira | 📊 **93%** |

### As quatro inteiras, na ordem

```
00:12:25   862,7 s   692 coletados   2 falhas   ← 🔴 as duas eram MINHAS
01:11:48   808,6 s   716 coletados   1 falha    ← o vazamento da P-246
01:30:21   743,3 s   718 coletados   2 falhas   ← o vazamento + uma VÍTIMA dele
02:0x      736,2 s   673 coletados   1 falha    ← só o restaurador se reportando
```

**A leitura, item por item:**

- **A primeira** achou dois defeitos reais, os dois meus, e os dois legítimos:
  o `.limit(5000)` de uma API que entrega 1000, e um guarda de janela fixa que
  o BLOCO D empurrou para fora. 🔴 **A bateria pagou o próprio custo na
  primeira rodada.**
- **Da segunda em diante, nenhuma falha é desta SPEC.** O que sobra é o
  vazamento de mutação da P-246 — documentado desde 22/08, estreitado aqui
  (§8.1), e o restaurador **falha de propósito** depois de limpar: *"restaura
  primeiro, reprova depois"*.
- 📊 **Os guardas cresceram 26** entre a primeira e a última (692 → 718
  coletados), quase todos escritos em resposta ao painel e ao juiz.

⚠️ **Gate ⑤ — a honestidade que ele exige:** a bateria **não fecha verde**. O
único vermelho não vem desta SPEC e não é regressão: é um guarda pré-existente
avisando que restaurou uma mutação vazada. 📊 Todos os guardas da SPEC-093 e os
vizinhos que ela tocou: **197 passed**.

---

## 7. Mudanças além do texto da SPEC (`CLAUDE.md` §11)

| classe | mudança | por quê |
|---|---|---|
| **BLOCKER** | `unblock_state` usa `assumido_por_humano`, não `destravado_por_humano` | 📊 o CHECK do banco recusa o valor da SPEC, e o `arquivar` filtra `.in(['travado','assumido_por_humano'])` — um sexto valor faria o caso **sumir da Fila** |
| **BLOCKER** | `actor_type: 'human'` → `'user'` no painel | 📊 o CHECK recusa `human`; 0 linhas em 27.985 eventos |
| **BLOCKER** | `note_manual_outbound` recebe `foi_humano` | o eco do robô gravaria "um humano assumiu" |
| **BLOCKER** | os corredores só ligam para quem escreve configuração | o BLOCO G desfazia o BLOCO A |
| **BLOCKER** | `typeof body.is_active === 'boolean'` restaurado | `Boolean("false") === true` **ligava** o agente |
| **BLOCKER** | corpo misto faz as duas coisas | o toggle era engolido em silêncio com 200 OK |
| **ESSENCIAL** | `route_sentinel` ganha `ATLAS_ALERTA_DESTINO` | esvaziar a allowlist matava o alarme de deriva |
| **ESSENCIAL** | anti-duplicata por conversa, em lotes de 1000 | `.limit(5000)` de uma API que entrega 1000 |
| **ESSENCIAL** | leitura de mensagens em **uma** query | 📊 86 conversas = 87 idas sequenciais |
| **ESSENCIAL** | `_reservar` devolve três estados | duplicata e erro contavam no mesmo balde |
| **VALIOSA** | `marcar_desligamento` removida | escritor morto com irmão vivo (§5) |
| **VALIOSA** | `sem_ancora` no resultado do "ligar tudo" | "ligou tudo" que ligou nada, com 200 |

⛔ **Escopo NÃO foi reduzido.** O item 1 do BLOCO B saiu porque **já estava
feito** (provado executando a função real), e o redesenho da tela do BLOCO G
saiu **por decisão registrada na própria SPEC v3**, com número medido.

---

## 8. Riscos remanescentes

1. 🔴 **O BLOCO D está pronto e desligado** (P-258). O caminho existe ponta a
   ponta e a prévia volta no religamento — **falta a tela de confirmação**.
   Enquanto ela não existir, nenhuma saudação sai, que é o desfecho seguro.
2. 🔴 **A posse não foi resolvida** (P-254). O BLOCO C fecha a metade do
   REGISTRO; a metade da POSSE (epoch/fencing) é a SPEC-086, calibrada pelo
   piloto, por decisão registrada.
3. ⚠️ **`allowlist_descartes` é por processo** — com mais de um worker, o número
   é o do worker que atendeu a requisição. Serve para *"está barrando?"*, não
   para *"quantos exatamente?"*. Escrito no código.
4. ⚠️ **O CHECK de `actor_type` não tem DDL no repositório** (P-255): o gate ⑧
   guarda o lado do código, não os dois lados.
5. ⚠️ **`INSURER_DISPATCH_LIVE` continua fora do ambiente** (P-168) — e por isso
   o Sentinela, que envia sem consultar `dispatch_live_enabled` (P-250), não
   morde. **Não é trava: é sorte.**

---

## 8.1 🔴 O vazamento de mutação, que esta SPEC estreitou (P-246)

A bateria inteira desta SPEC **terminou com `backend/scripts/rubrica.py`
mutado** — a terceira ocorrência de um defeito documentado desde 22/08.

📊 **O diagnóstico, com linha de controle:**

```
rodando o guarda suspeito SOZINHO .......  52 verdes, ÁRVORE LIMPA
tempo dele sozinho ......................  14 s
TETO_SEGUNDOS do harness ................  120 s   (8× de folga)
guardas que o harness roda ..............  273
dos quais TOCAM rubrica.py ..............    2  — e os DOIS limpam sozinhos
```

🔴 **A limpeza já existia no lugar certo** (`test_a_arvore_ficou_limpa_no_fim`)
— o que faltava era o **alvo**: `ARQUIVOS_COMPARTILHADOS` era uma tupla de
**dois nomes escrita à mão**, e `rubrica.py` nunca esteve nela.

✅ **Consertado nesta SPEC:** a lista passou a ser **derivada por `ast` dos
próprios `MUTACOES` dos guardas**. 📊 De **2 para 6** alvos. Dois guardas novos
impedem a volta — um exige cobertura de todo arquivo declarado, o outro **muta
`rubrica.py` de verdade** e prova que a restauração o alcança.

⚠️ **E o conserto criou um falso positivo, também consertado:** com a lista mais
larga, a marca `_DESLIGADO` solta acusava a constante legítima
`_DESLIGADO = ("0","false","no","off","nao","não")`. Estreitada para a forma de
chave — 📊 provado que **ainda pega** `# MUTACAO`, `DESLIGADO PELA MUTACAO` e
`"schedule_agendado_DESLIGADO"` (o vazamento original da SPEC-085), e que o
código legítimo passa.

> 🔴 **Um guarda que acusa código legítimo ensina a ignorar o guarda.**

⚠️ **E o vermelho cai em quem estiver rodando na hora:** o guarda que apareceu
vermelho na bateria 📊 passa sozinho em 6 s com a árvore limpa. Era **vítima**.

---

## 9. Pendências abertas por esta SPEC

`P-249` `work_effects` sem DDL e sem escritor ·
`P-250` o Sentinela envia sem consultar o portão ·
`P-251` a rota que credita o humano não tem consumidor de UI ·
`P-252` `send_message` paralelo com zero importadores ·
`P-253` `conversations.resolvido_em` sem escritor ·
`P-254` a corrida do epoch ·
`P-255` o CHECK de `actor_type` sem DDL ·
`P-256` a rota da saudação recebe `company_id` do chamador ·
`P-257` 🔴 `git checkout --` apagou trabalho não commitado, de novo ·
`P-258` o envio da saudação continua sem tela de confirmação.

---

## 10. Canário

⛔ **Não executado, e é deliberado:** o canário Amandus → Resulta → AutoFleet
exige ligar o atendimento, e as travas desta sessão proíbem isso. O que foi
possível verificar sem ligar nada:

```
📊 agents attendance ......... 4 linhas, is_active=true em 0
📊 platform_sends (24h) ...... 0
📊 saudacoes_enviadas ........ 0
📊 work_events travamento.* .. 0
📊 tenant_corridors .......... 2 linhas, 2 active
```

O canário fica para o dia em que o Founder apertar o botão — e a prévia do
BLOCO D é o que ele vai ver antes.
