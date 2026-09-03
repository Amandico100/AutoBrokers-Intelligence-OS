# PROTOCOLO AAA — AS EVIDÊNCIAS

> **Leitura UMA VEZ.** Este arquivo existe para que o
> [`PROTOCOLO-AUTOBROKERS-AAA.md`](PROTOCOLO-AUTOBROKERS-AAA.md) possa ser curto.
> Ele guarda **como cada regra foi medida** e **por que cada versão mudou**.
>
> ⛔ **Não entra no bootstrap do `CLAUDE.md` §2.** Quem executa lê o protocolo;
> quem quer saber por que uma regra existe vem aqui.

---

## 📊 A MEDIÇÃO QUE PRODUZIU A v9 — 25/08/2026

Quatro lentes em paralelo, cegas entre si, sobre a pergunta *"por que ficou lento?"*.

### ① Onde o tempo foi

Janela: 24/08 10:43:44 → 25/08 00:33:04 = **829 min (13h49)**, 21 commits.

```
min    %      docs   codigo   fase
178   21,5   1.179       0    Protocolo v2→v4
 75    9,0   1.558       0    SPEC-085 v1 + as 3 voltas de juiz
 71    8,6     116     196    P-183: fazer o pytest rodar
 24    2,9     351       0    Prompts de delegacao
 77    9,3     275     231    AQUECIMENTO: 15 perguntas + auditor
405   48,8   1.094   5.595    EXECUCAO da SPEC-085
```

📊 **Tempo até a primeira linha de código de produto: 565 min = 9h25.**

### 🔴 ② A LINHA DE CONTROLE — e é ela que dá direito à conclusão

Mediana do intervalo entre commits:

```
16–17/08  sem juiz, sem protocolo   58 commits   20,5 min
18–20/08                            18 commits   10,0 min
21/08     o juiz aparece            32 commits   15,0 min
22–23/08  juiz, sem protocolo       78 commits   25,5 min
24–25/08  PROTOCOLO                 20 commits   21,7 min
```

**O tempo por commit não mudou.** Os *"15–20 minutos"* que o Founder lembra são a
mediana de 16–17/08 — **20,5 min** — e hoje ela é **21,7**.

```
fração do relógio que NÃO produz código de produto
   16–17/08  CONTROLE      7,6%
   22–23/08                1,0%
   24–25/08  PROTOCOLO    35,7%
```

> **As 5–8 horas não são um passo que ficou lento. São a fila que passou a
> existir antes do primeiro passo.**

📊 **E a execução ficou 2× mais rápida:** 13,8 linhas/min contra 7,1 em 22–23/08.

### ③ O pedágio de entrada

```
a leitura obrigatoria do CLAUDE.md §2 + a SPEC = 864.896 bytes
   crescimento:  596.625 (21/08) → 682.356 (23/08) → 781.275 (25/08)   +31%
   PENDENCIAS.md sozinho:  465.187 bytes = 54%, 233 entradas, 5,6% fechadas
   o prompt de delegacao: 9.362 bytes.  RAZAO 92×.
```

### 🔴 ④ A inversão do laço

```
23/08  os juizes rodaram DEPOIS do codigo  → 1.008 linhas de conserto de PRODUTO
24/08  as 3 voltas rodaram ANTES, sobre um documento
                                            →   610 linhas de DOCUMENTO, 0 de codigo
razao docs/codigo:  0,24 → 0,74
```

### ⑤ Quanto custou o laço de juiz — e ele é barato

📊 SPEC-085, três voltas: **59 min** (13 min cada, medido pelos timestamps dos
arquivos de trabalho). SPEC-084, sete voltas: **52 min**.
📊 SPEC-083: nove versões, 14:19→18:32 = **4h13**, oito voltas em série. Os deltas
colapsam — v5 em 11 min, v6 em 7, v7 em **4**. **O teto de 3 a encerraria na v4:
2h51 economizadas.**

---

## 📊 DE ONDE VEIO A QUALIDADE — 15 defeitos reais, com o mecanismo

| defeito | mecanismo | commit |
|---|---|---|
| a FASE 1 inteira sobre premissa falsa (o mascarador não existe) | **juiz novo, contexto limpo** | `4f4be62` |
| mascarar ali quebraria a URA (`output_summary` é o payload de restauração) | **juiz novo** | `4f4be62` |
| `A.2` tornaria todo `needs_human` imortal na varredura de órfãos | **juiz novo** | `4f4be62` |
| `E.1` apagaria a Fila e devolveria conversas DUPLICADAS ao segurado | **juiz novo** | `4f4be62` |
| `case_id` CONTÉM o telefone do segurado — 12 de 12 | **conferir o DADO, não o código** | `081c7d0` |
| `_normalizar_destino` fabrica telefone a partir de rótulo | **aquecimento** | `e3686f9` |
| `pytest tests/` abortava a sessão; 48 vermelhos invisíveis | **aquecimento** | `e3686f9` |
| o Vigia morre inteiro sem Redis — **o produto cala** | **RED TEAM** | P-238 |
| duas retomadas simultâneas sem lock | **RED TEAM** | P-237 |
| o desfecho apagava da Fila quem ainda espera gente | **juiz de confirmação** | `e527705` |
| a armadilha do NULL: `.not_.like()` devolve 0; `.or_()` devolve 2 | **medir contra o banco** | `081c7d0` |
| *"33,2% travam"* media o time HUMANO da corretora | **enquadramento do Founder + medição** | `20a9f5d` |
| mutação vazada desligava a âncora do único acionamento real | **linha de controle** | `bb71913` |
| a QUARTA cadeia de handoff | **`grep` por conceito + "reporta fora do escopo"** | P-235 |
| o guarda ficava verde sob duas mutações | **mutação** | report:476-506 |

### 🔴 Nota por mecanismo — achados ÷ custo

```
juiz de contexto limpo (3ª volta)   98   4 que quebrariam producao, EXCLUSIVOS
aquecimento de 15 perguntas         96   PII exfiltravel + a suite inteira falsa
red team                            94   P-238: o produto CALA; ninguem mais achou
juiz de confirmacao pos-conserto    92   2 consertos do painel viraram defeito
mutacao                             90
linha de controle nos gates         88
painel de 4 lentes                  85   13 achados, sobreposicao ZERO
conferencia do DADO (vs. codigo)    84
grep por conceito                   80
"reporta fora do escopo"            72
teste do produto                    65   nao ACHA; regula o laco
teto de 3 voltas                    15   inerte por redacao ate a v6
🔴 juiz RETOMADO (volta 2)          05   VALOR NEGATIVO
```

> **"Com metade dos passos, pelo menos oito defeitos reais vão para produção,
> e cinco alcançam o segurado."**

---

## 📊 AS SETE PROPOSTAS EXTERNAS, JULGADAS CONTRA ESTE REPOSITÓRIO

```
#3 context diet                78   o maior custo medido. VALE.
#4 stall detection             62   o teto de 3 ja pega a maior parte;
                                    o que sobra e o detector de achado repetido
#5 gates hierarquicos          45   nao ha mapa teste→modulo: 273 de 279 sao scripts
#1 cohesion partitioning       35   o acoplamento e tao extremo que particionar
                                    e IMPOSSIVEL, nao malfeito
#7 concorrencia 3–5            15   📊 o numero nunca foi 12: sempre ≤5
#6 Fast/Standard/Critical      12   ja existe DUAS vezes: a grade 3×3 e os 5 modos
#2 critical-path first          8   nao ha fila: a SPEC E a ordem
```

---

## O HISTÓRICO DAS VERSÕES — v1 a v8

## 11. O QUE MUDOU DA v1 PARA A v2, E POR QUÊ

📊 **A v1 foi submetida ao próprio protocolo e reprovou com sete blockers.** O
laço não travou julgando a si mesmo — a §1 funcionou e rebaixou seis achados do
juiz a pendência. O que falhou foi a §2, que era a parte inventada e não medida.

| # | o defeito da v1 | o conserto |
|---|---|---|
| B1 | o arquivo não estava commitado nem no `CLAUDE.md` — nenhum agente o abriria | commitado, e no bootstrap §2 e na ordem de autoridade §3 do `CLAUDE.md` |
| B2 | a conta dava **três respostas** para uma palavra numa mensagem, **9 agentes** para um `COMMENT` e **zero** para 117 commits em produção | §2 refeita: RISCO × SUPERFÍCIE, piso por EFEITO, e os seis casos re-pontuados em §2.6 |
| B3 | a conta não governava 3 dos 4 modos, e dava 0 para toda avaliação de ideia | §2.5: a conta vale para mudança, não para investigação; tabela dos modos em §7 |
| B4 | §3 e §4 discordavam sobre quem declara pendência — a única alavanca que para o laço | §4: o juiz **classifica**, o orquestrador **registra**, e o rebaixamento vai **escrito** |
| B5 | STALLED não é nenhuma das oito condições de parada do `CLAUDE.md` §10 — nascia morta | §6: STALLED é **classificação**, não parada. Ou cai numa das oito, ou entrega e avança |
| B6 | o laço era cópia do que já falhara, e não revogava *"reprovação inacionável não conta como volta"* | §6 declara precedência, revoga a cláusula, e **toda volta conta** |
| B7 | não havia modo para incidente, e a conta **atrasava** a volta do produto | §7: MODO INCIDENTE, elenco mínimo, conserto reversível, juiz adiado |

### A VOLTA 2 — mais cinco, e dois deles o conserto da v1 abriu

📊 **A prova de que a §2 funciona veio primeiro:** o juiz novo aplicou as §2.1–§2.5
aos seis casos **antes** de abrir a §2.6, e chegou ao **mesmo time nos seis**. Isso não
é palpite — é reprodução por um segundo leitor.

| # | o defeito da v2 | o conserto |
|---|---|---|
| 1 | 🔴 a isenção de `GRANT` e `índice` da §2.4 dava **"ninguém"** à única migration de vazamento entre corretoras do repositório, e ao índice que **é** a fronteira estrutural | só o `COMMENT` fica isento; o piso passa a dizer **"altera dado, estrutura, TRAVA ou QUEM PODE LER"** |
| 2 | **o B6 não fechou**: a cláusula estava viva também em `SPEC-084 §6.3`, e eu não rodei o `grep` que a §7 manda rodar | revogada nas duas, o §6 nomeia **qualquer SPEC**, e traz o comando de verificação escrito |
| 3 | a trava *"não sei onde isto pega"* dava SUPERFÍCIE **3** a qualquer linha de prompt — **nove papéis para duas linhas**, em 13% dos commits do mês | §2.2: **dois "não saber"**. Não saber onde pega é superfície; não saber se o modelo obedece é **prova** |
| 4 | o VERIFICADOR MECÂNICO da §3 listava exatamente os gates que deixaram o produto **1h40 no chão** com tudo verde | §3 passa a exigir `test:rotas-montam` + `next start` + **uma requisição a rota que executa código** |
| 5 | §2.5 e §8 davam respostas opostas à mesma frase — *"três respostas"* de novo, na seção escrita para curar isso | a fronteira **CONSULTA PONTUAL × VARREDURA**, escrita uma vez e citada nos dois lugares. MODO IDEIA vira **MODO INVESTIGAÇÃO** |

🔴 **E o defeito nº 2 é o mais instrutivo do documento inteiro:** a §7 manda *"depois de
cada reescrita, `grep` por cada conceito que mudou de definição — releitura nunca achou
nenhum deles"*. **Eu escrevi a regra e não a rodei.** O juiz rodou, e achou. A regra
pegou o autor dela — que é o único teste que vale.

**As pendências que o juiz achou e que reprovaram o teste do produto** — evidência
que não reproduzia na §1, a alegação inflada sobre a primeira volta, a referência
`allianz` que a SPEC-084 já rejeitara como outlier, e a §5 sem "quando" nem "onde"
— **foram consertadas junto**, porque o custo era uma linha cada.

### A VOLTA 3 — juiz novo, contexto limpo, sem ver as anteriores

🔴 **Foi a volta desenhada para testar a ancoragem** (a §6 manda que a terceira seja
um juiz que não vê as voltas anteriores). Ele escolheu **sete casos reais do
repositório que este documento não usa como exemplo**, pontuou sozinho, e julgou cada
time. 📊 **Em quatro dos sete o time saiu certo e ele disse isso** — e em dois deles
*"sem o piso, a conta erraria os dois casos de segurança"*.

| # | o defeito da v3 | o conserto |
|---|---|---|
| 1 | 🔴 o VERIFICADOR MECÂNICO era **incondicional na §6** e **opcional na §2.3** — e a célula que o dispensa aceita `next.config.js`, a classe que derrubou o produto por 1h40. 📊 E não há rede: `grep -rn "rotas-montam" .github/` → **vazio** | ele deixou de ser papel que a conta convoca e virou **passo do laço**. A célula "ninguém" dispensa o juiz, nunca o passo ② |
| 2 | *"lote"* (§2.2) e *"por unidade de trabalho"* (§7) davam **9 papéis ou 90** para a mesma SPEC-089 — e **"unidade de trabalho" nunca era definida** | o lote paga **uma** passada de enquadramento cujo entregável é a lista das unidades; cada unidade pontua sozinha. E a definição: *"a menor coisa que dá para entregar e provar sozinha"* |
| 3 | a §1 listava `relatório` como destino da corretora — **reabrindo o laço que ela existe para fechar** | *"o relatório que o PRODUTO gera — nunca o relatório de execução da SPEC"* |
| 4 | o MODO INVESTIGAÇÃO aplicava o elenco de **avaliar ideia** a auditoria e medição, e *"× largura"* não tinha teto nem definição | **dois elencos** — IDEIA e AUDITORIA, este com MEDIDOR, CÉTICO DA MEDIDA, HISTÓRICO e JUIZ DO RISCO — e a largura tem **teto de quatro frentes** |

⚠️ **E dois números meus não reproduziram**, o que o `CLAUDE.md` §12.1 chama de defeito
de revisão: *"274 `CREATE INDEX`"* estava colado a uma frase sobre `CREATE UNIQUE
INDEX` (📊 são **40**, de 314 no total), e *"26 das 66 SPECs"* não reproduz com
recorte nenhum (📊 **14 de 65** estrito, **24** largo). **Os dois foram corrigidos com
a consulta ao lado.**

### 🛑 A PORTA ③ — e o protocolo se aplicando a si mesmo

**Três voltas. O juiz da terceira não liberou.** Pela §6, isso obriga uma
classificação, e a classificação é esta:

```
É uma das oito condições de parada do CLAUDE.md §10?
   NÃO — não há risco de perda de dado, decisão comercial, conflito canônico,
   P0 de segurança, ação física do Founder, mudança de escopo, custo
   extraordinário, nem falta de acesso.

→ 🔴 NÃO PARA. Os quatro blockers foram consertados, o que sobrou está
  registrado abaixo, e o documento ENTREGA.
```

### ✅ AS QUATRO QUE SOBRARAM DA VOLTA 3 — fechadas na v5

🔴 **E uma delas eu classifiquei errado.** Escrevi que *"nenhuma das quatro muda o
time"*. ⚠️ **A das células com `+` muda:** `+ verificador` sem dizer a que soma deixa o
leitor montar **três ou cinco pessoas** para a mesma nota. **Isso é blocker pela §1, e
eu chamei de redação.** 🔴 O teste do produto é fácil de aplicar ao achado dos outros e
difícil de aplicar ao próprio — registrado aqui porque volta a acontecer.

| # | o que era | o conserto |
|---|---|---|
| 1 | as células com `+` não diziam a que somavam — **3 ou 5 pessoas para a mesma nota** | as **nove células por extenso**, nenhuma soma implícita |
| 2 | os rótulos (*"ninguém sente"*) podiam contradizer a aritmética | são **típicos, não definições** — **se discordarem, a soma vence** |
| 3 | a listagem das pendências era do INVESTIGADOR, ausente da maioria das células | onde não houver, é do **ORQUESTRADOR** |
| 4 | o verificador rodava *"migrations"* sem conhecer a `MIGRATIONS-AUTHORITY.md` | nomeada, **com a razão medida: o ledger mente** — o VERIFY confere o objeto |

✅ **O INTEGRADOR** já ganhara gatilho na v4: 3 ou mais unidades no mesmo lote.

✅ **E A ÚLTIMA FECHOU: a SPEC-085 rodou sob ele**, e o que a execução ensinou está na
§6.0.1 e na §6.0.2 — **as duas primeiras regras deste documento que vieram de MEDIR, e
não de ler.** 🔴 As duas contradizem o que eu tinha escrito por hipótese, e as duas
tornam o laço mais barato: a volta 2 deixa de produzir uma nota falsamente alta, e o
teto passa a ser alcançável.

⚠️ **O que continua por medir:** o protocolo governou a **escrita** de uma SPEC. **Ainda
não governou a EXECUÇÃO de nenhuma** — nem um builder, nem um verificador mecânico, nem
um red team rodaram sob ele. **Isso fecha na 085 executada.**

⚠️ **O que continua por medir:** 💭 **nenhum orquestrador rodou sob este protocolo
ainda.** Tudo aqui é análise de documento contra repositório. **A prova é a
primeira SPEC executada sob ele** — e o número a vigiar é se a §2 continua
separando os casos quando eles não forem os seis que a calibraram.

---

# 🔴 25/08/2026 — o neto que mutava o corredor

📊 **O mutador nunca foi um guarda desobediente. Era o próprio harness matando
errado.**

```
test_a_regua_nao_tem_furo.py ............  16,3s
VM.verificar → 12 mutações ..............  12 × 16,3 ≈ 196s
+ o exec_module in-process ..............  ≈ 212s por medição
test_duas_medicoes lança DUAS ...........  ≈ 425s
TETO_SEGUNDOS ...........................  120     🔴
```

`subprocess.run(timeout=)` faz `kill()` + `communicate()` no estouro. ⚠️ **No
Windows `kill()` é `TerminateProcess`, que mata UM processo — não a árvore.** Os
netos `medir_rota.py` sobreviviam ~5 min **mutando `corridor_playbooks.py` doze
vezes cada**, e a mutação caía na janela de quem estivesse rodando na hora.

📊 A ordem confirmou: o mutador é o índice **60** em `sorted(GUARDAS)`; os
acusados eram **110, 122, 123, 127, 133** — todos depois dele.

### 🔴 E a quarentena escondia a causa

`test_duas_medicoes` está em `QUARENTENA` como `xfail`. O `pytest.fail` do
estouro virava `xfailed` e **sumia do relatório**. O guarda certo ficava
vermelho, e quem investigasse procuraria no lugar errado.

> ⛔ **Regra nova, e ela custou um dia:** `xfail` num guarda que LANÇA PROCESSO
> esconde o efeito colateral junto com a falha. Quarentena serve para asserção
> vencida — **nunca para quem tem filho.**

### Os dois consertos, e por que são estes

```
🔴 o estouro mata a ÁRVORE     taskkill /F /T (Windows) · killpg (POSIX)
🔴 a trava é do KERNEL         msvcrt.locking / fcntl.flock sobre 1 byte
   ⛔ nunca O_EXCL, nunca unlink ao soltar
   o lock pertence ao HANDLE: o SO o solta quando o dono morre —
   sem heurística de idade, sem PID, sem ninguém apagando `.lock`
🔴 a espera da trava < o teto de quem espera    900s → 90s, contra TETO=120
   uma espera maior que o teto de quem espera não é paciência:
   é a garantia de que ninguém nunca vai chegar a esperar
```

📊 **Provado por `test_o_timeout_nao_deixa_neto_vivo.py`, 5 testes** — e o que dá
direito à conclusão é a **linha de controle**: matando só o pai, o neto
**sobrevive**; matando a árvore, **morre**. Sem ela os dois passariam por acaso.

### E o passo 2º está instrumentado

`backend/tests/conftest.py` passou a escrever uma linha por rodada de pytest —
quando, quanto, sobre o quê, em que commit, local ou CI. **Na próxima SPEC o
"9–14 rodadas" deixa de ser 💭 e vira 📊**, e só então o passo 3º é decidível.

⚠️ **E uma correção de quem escreveu a regra:** *"13 commits × 16m44 = 3h37"* foi
dito com cara de medição. 🔴 **Commit não é rodada.** O custo por rodada estava
medido; o número de rodadas era chute. É a §12.1 contra o próprio autor.

---


---

# 📊 O DIÁRIO DA v9 → v10 — o que saiu do documento normativo

> ⚠️ **Isto é HISTÓRICO, não regra.** Saiu do `PROTOCOLO-AUTOBROKERS-AAA.md` em
> 30/08/2026, quando a auditoria mediu que **37% do protocolo era diário de
> bordo datado** — e um protocolo que ninguém consegue ler inteiro é um
> protocolo que ninguém segue.
>
> 🔴 **As regras que estas medições produziram continuam no protocolo.** O que
> saiu foi a narrativa de como elas foram descobertas.

## ⚠️ O QUE A v9 CONSERTA — e o diagnóstico de todo mundo estava errado

O Founder disse: *"tarefas de 20 minutos agora levam 5 a 8 horas"*. Quatro lentes
foram medir. **A resposta contraria o que eu, ele e o consultor externo supúnhamos.**

📊 **Mediana do intervalo entre commits, cinco janelas de `git log`:**

```
16–17/08  sem juiz, sem protocolo   58 commits   20,5 min   ← a memória do Founder
24–25/08  COM o protocolo           20 commits   21,7 min
```

> 🔴 **O tempo por commit não mudou. E a execução ficou DUAS VEZES mais rápida:**
> 📊 **13,8 linhas/min** contra **7,1** na semana anterior.

**O que mudou foi a fila antes do primeiro passo:**

```
fração do relógio que NÃO produz código de produto
   16–17/08  CONTROLE ......  7,6%
   22–23/08  ..............   1,0%
   24–25/08  PROTOCOLO ..... 35,7%

📊 tempo até a primeira linha de código da SPEC-085:  9h25
```

**E o laço de juiz — que todos apontavam — custou 59 minutos.** 📊 As três voltas
da SPEC-085: 13 min cada. Sete voltas da SPEC-084: 52 min. **O juiz é barato.**

### 🔴 As duas causas reais, medidas

**① O PEDÁGIO DE ENTRADA.** 📊 A leitura obrigatória do `CLAUDE.md` §2 soma
**864.896 bytes**, e **cresceu 31% em quatro dias** (596 KB em 21/08). Destes,
**465 KB são o `PENDENCIAS.md`** — 233 entradas, 5,6% fechadas.
📊 **O prompt de delegação tem 9 KB. O que ele manda ler tem 865 KB. Razão 92×.**

**② O LAÇO FOI INVERTIDO — e passou a comprar documento em vez de produto.**

```
📊 23/08  os juízes rodaram DEPOIS do código
          → compraram 1.008 LINHAS DE CONSERTO DE PRODUTO
📊 24/08  as três voltas rodaram ANTES, sobre um documento
          → compraram 610 linhas de DOCUMENTO e ZERO de código
📊 razão docs/código:  0,24  →  0,74
```

> ## 🔴 O protocolo não deixou a execução lenta. Ele criou uma fila de 9h25 antes dela, e mudou o alvo do juiz de CÓDIGO para DOCUMENTO.

**A v9 ataca as duas — e começa por si mesma.** 📊 A v8 tinha 58 KB e virou o
segundo maior arquivo do bootstrap. O histórico, as medições e a prova de cada
regra foram para [`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md) —
**leitura uma vez, nunca a cada sessão.**

---

---

### 📊 25/08 — a bateria aberta ao meio, e a ordem deixou de ser teoria

```
os 296 guardas-script     7m14      45% do relógio
o resto do pytest         ~9m       55%
                          ─────
                          16m10     550 passed · 45 xfailed
```

🔴 **E dos 296, só 87 são perigosos.** O critério é mecânico — o guarda lança
processo (`subprocess`, `Popen`, `Thread`), escreve arquivo, toca a rede, ou
importa o compartilhado (`corridor_playbooks`, `replay`):

```
209  leitores puros    →  podem rodar EM PARALELO
 87  perigosos         →  ficam SERIAIS
```

💭 A 4 processos: `7m14 → ~3m30`. **~48 minutos por SPEC**, sem cortar um teste.

## 📊 26/08 — o passo 2º está MEDIDO, e ele desmente quem o escreveu

**Pela primeira vez no projeto, o número de rodadas da bateria numa SPEC não é
chute.** O diário do `conftest.py` contou a SPEC-093 inteira:

```
rodadas de pytest no total ......  115
   bateria INTEIRA ..............    9
   parciais (um teste, um arquivo) 106

relógio esperando a suíte .......  2h00
   só as inteiras ...............  1h49
   cada uma .....................  12,0 · 12,3 · 12,4 · 13,4 · 13,5 · 14,4 · 14,5 · 17,1
```

E a conta que importa:

```
SPEC-093, do primeiro ao último commit ...  4,0 horas
   das quais a bateria ...................  2,0 horas   =  50%
```

### 🔴 O que isto derruba

⚠️ **Eu escrevi *"13 commits × 16m44 = 3h37"* com cara de medição.** O medido é
**2h00** — o chute estava **80% alto**. 📊 E a causa é a que a §12.1 descreve:
**commit não é rodada.** Foram 11 commits e **9** rodadas inteiras, e as 106
parciais custaram só ~10 minutos no total.

> **A aritmética sobre uma unidade medida não herda a marca 📊 da unidade.**

### ✅ E o que confirma

📊 A paralelização entregou: as nove inteiras deram média **13m18**, contra
**16m10** antes. Sem ela, as mesmas nove teriam custado **2h26** — a economia
real foi de **~26 minutos nesta SPEC**.

### 🔴 E o passo 3º agora é decidível — o que ele não era

**Nove rodadas inteiras para seis blocos.** A alavanca que sobra não é rodar mais
rápido: é **rodar menos vezes**.

```
hoje       9 inteiras × 13m18  =  2h00
o alvo     4–5 inteiras        =  ~1h      →  a SPEC cai de 4h para ~3h
```

⚠️ **E o pré-requisito continua o mesmo:** 📊 273 dos arquivos de teste são
scripts, **não existe mapa teste→módulo**, e sem ele *"rodar só o que prova a
leaf"* é chute. **O mapa é o trabalho, não o corte.**

⛔ **O que NÃO fazer:** cortar rodada por regra de tempo ("uma a cada duas
horas"). 📊 As 106 parciais são baratas e são o que o executor usa para trabalhar
— cortá-las economiza 10 minutos e cega o ciclo curto.

---

## ✅ 25/08 — o passo 1º está FEITO

📊 **O mutador nunca foi um guarda desobediente: era o harness matando errado.**
`subprocess.run(timeout=)` mata com `TerminateProcess`, que no Windows derruba
**um processo, não a árvore** — e os netos seguiam mutando o corredor por
minutos, na janela de quem estivesse rodando.

```
🔴 o estouro mata a ÁRVORE      taskkill /F /T · killpg
🔴 a trava é do KERNEL          msvcrt.locking / flock sobre 1 byte
   ⛔ nunca O_EXCL, nunca unlink: o lock é do HANDLE, e o SO o solta
      quando o dono morre. Sem idade, sem PID, sem ninguém "destravando".
🔴 a espera da trava < o teto de quem espera     900s → 90s, contra TETO=120
```

> ⛔ **A regra que custou um dia:** `xfail` num guarda que **LANÇA PROCESSO**
> esconde o efeito colateral junto com a falha. Quarentena é para asserção
> vencida — **nunca para quem tem filho.**

📊 Provado por `test_o_timeout_nao_deixa_neto_vivo.py`. O que dá direito à
conclusão é a **linha de controle**: matando só o pai o neto **sobrevive**;
matando a árvore, **morre**.

**E o passo 2º está instrumentado:** `backend/tests/conftest.py` escreve uma
linha por rodada. Na próxima SPEC o "9–14 rodadas" vira 📊, e só então o 3º é
decidível. ⚠️ *"13 commits × 16m44 = 3h37"* foi dito com cara de medição —
🔴 **commit não é rodada**, e a §12.1 vale contra quem a escreveu.

📎 O diagnóstico inteiro, com os tempos e a ordem dos índices, está em
[`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md).

---

## ⛔ Mas o passo 1º deixou de ser precaução e virou defeito medido

📊 **Hoje, numa rodada real, o mesmo guarda deu os dois resultados:**

```
no lote:   test_o_comparador_ve_resposta_errada    FALHOU
sozinho:   o mesmo guarda                          PASSOU (16,21s)
```

🔴 **É o processo solto do `test_todos_os_guardas_script_rodam.py`, vivo.** Alguém
lança uma medição, não a espera, e a mutação de `corridor_playbooks.py` cai na
janela de quem estiver rodando na hora.

> ⛔ **Paralelizar antes da trava não alarga a janela — alarga QUEM CAI NELA.**
> O mutador continua serial; o que muda é o número de vítimas por janela. Com
> 209 em paralelo, um vermelho aleatório vira rotina — **e vermelho que vira
> rotina é vermelho que ninguém lê** (`CLAUDE.md` §9.3).

⚠️ **E a suíte segue crescendo:** 322 em 24/08 · 463 em 25/08 · **595** depois da
SPEC-092. **+85% em dois dias.** A conta piora sozinha.

⛔ **MAS A ORDEM DO CONSERTO NÃO É ÓBVIA, e invertê-la troca um problema de tempo
por um de PERDA DE DADO:**

```
1º  A TRAVA DA BATERIA (§10, acima).  📊 É a bateria rodando na árvore
    compartilhada que apagou dois consertos. Afinar QUANDO ela roda sem mudar
    ONDE ela roda troca lentidão por trabalho perdido.
    🔴 **E em 25/08 isto deixou de ser risco e virou medição:** um guarda
    vermelho no lote e verde sozinho, no mesmo dia. A trava é conserto de
    defeito ATIVO — não é preparação para o paralelismo, é pré-requisito dele.

2º  MEDIR QUANTAS VEZES ela roda de fato numa SPEC. 💭 9–14 é estimativa,
    não medição — e este documento não aceita de mais ninguém o que aceitaria
    de si (§11).

3º  SÓ ENTÃO os gates por nível: leaf prova a leaf, branch prova a integração,
    root roda tudo.
    ⚠️ 📊 Hoje **273 dos 279 arquivos de teste são scripts**, não pytest —
    **não existe mapa teste→módulo**, e sem ele "rodar só o que prova a leaf"
    é chute. O mapa é pré-requisito, não detalhe.

⛔ E antes de tudo: 📊 `grep -rn "rotas-montam" .github/` → **vazio**. O gate que
   o `CLAUDE.md` §9.1 existe para impor não roda. **Afinar bateria antes de
   fechar esse buraco é afinar o lado errado.**
```

---

# 📊 O DIÁRIO DA v10 → v11 — 03/09/2026

> ⚠️ HISTÓRICO, não regra. O que saiu do protocolo e por quê, medido.

## O que a auditoria de entrada mediu (Fable 5.1, 02–03/09/2026)

```
📊 composição da v10   965 linhas · 40,6 KB · núcleo §0–§5 = 16,2 KB
   320 linhas dentro de cerca (regra) · 221 de prosa · 41 de prosa contando história
   comando: awk sobre cercas/tabelas/prosa + grep -cE '📊|mediu|custou|nasceu'
📊 conferibilidade    o guarda tinha 20 asserções, TODAS sobre o texto do protocolo.
   0 de 9 relatórios com EXECUTION CARD · 0 com FAIXA DE RELÓGIO · 0 com auditoria externa
   (card e faixa entraram em 02/09, DEPOIS de todas as execuções — não é desobediência)
📊 pesquisa           133 URLs distintas em 10 research-packs (12.116 linhas) ·
   ZERO em qualquer SPEC convertida · ZERO em qualquer relatório
   comando: comm -12 entre os conjuntos de URL de cada par RP × SPEC
📊 o relógio real     nenhuma SPEC teve janela perto de 24h.
   085 = 10,6h (9h25 antes do primeiro código) · 086+087+089+090 = 11,9h as quatro,
   intercaladas na noite de 26/08 · 092 = 6,3h (6min45 antes do primeiro código) ·
   093 execução = 0,6h · 088/091 (02/09) = 4,1h e 4,5h SÓ de reescrita de documento
   comando: git log --all --format='%h|%ad|%s' --date=iso, filtrado por SPEC no subject
📊 a bateria          709 rodadas de pytest em 26/08 (18 inteiras) para quatro SPECs;
   suíte inteira = 13–16 min. Fonte: backend/.diario-da-bateria.jsonl (780 linhas)
📊 os 12 defeitos     de 02/09: 11 eram "afirmei por leitura o que um comando decide"
```

## As conclusões que mudaram o documento

1. **O protocolo não estava lento; foi violado na direção que ele proíbe.** As três
   rodadas de três juízes sobre as SPECs 088 e 091 em 02/09 eram painel sobre
   documento, que a §5.1 veda desde a v9. Não se acrescentou regra: encurtou-se o
   texto para que a regra existente fosse lida.
2. **A conferibilidade estava no objeto errado.** O guarda passa a olhar relatórios,
   SPECs e pacotes (blocos 7–9 do `test_o_protocolo_tem_policia.py`).
3. **A pesquisa não tinha porta de entrada.** Nasce a §7.3 e o papel PESQUISADOR.
4. **Onze de doze defeitos tinham o mesmo mecanismo.** Nasce a §0.4, A REGRA DO COMANDO.
5. **A grade 3×3 com nove rituais nunca foi executada (0 de 6).** Vira três níveis
   (LEVE · PADRÃO · CRÍTICO) derivados das mesmas duas contas.
6. **A bateria é o maior sumidouro.** A §10 passa a dizer QUANDO a suíte inteira roda.
7. **A política de modelo virou regra** por decisão do Founder em 02/09: Fable
   orquestra, Opus executa e julga.
8. **Nasce o MODO LOTE LOCAL** (§8), por pedido do Founder: trabalho de volume que
   custaria API roda num chat dedicado do Claude Code, com o código do produto.

## O que saiu do texto normativo e mora aqui

- §0.1 antiga inteira (a história "2 de 6 rodaram o painel", 47 × 19 achados, 4% × 50%).
- A narrativa da §1 (865 KB, +31% em quatro dias, PENDENCIAS = 54%).
- A história da §3.4 (SPEC-085 e o `dispatch_router.py`).
- As histórias da §5.1 (1.008 vs 610 linhas), §5.2 (4h13 da 083, cinco erros na 085),
  §5.3 (+11 e +25 do juiz retomado), §6.1 (093 e 089), §7.2 (2min22 do eletricista).
- As três medições da suíte na §10 (19m01 · 16m26 · 14m46) e a conta dos 95 min da 085.
- A §11 longa de telemetria: ficou em cinco linhas que o guarda confere.
- A §13 de "consenso de fora × calibração deste projeto".

Todas as regras que essas histórias produziram continuam no protocolo, sem a história.


---

## DIÁRIO DA v11 → v11.1 · 03/09/2026 · decidido pelo orquestrador depois da SPEC-093-B

📊 **O que as duas primeiras execuções sob a v11 mediram** (relatórios 088 e 093-B em `reports/`):

```
                              088 (PADRÃO)         093-B (CRÍTICO)
faixa declarada / realizada   6–9h / 3h35          8–13h / 7h15
painel                        3 lentes             4 lentes + red team
blockers únicos do painel     5                    7
conserto criou defeito?       não                  SIM (recall −9,5%, pego pelo juiz de confirmação)
auditoria externa             —                    2 BLOCKERS que NENHUMA das 5 frentes viu
```

**Emenda A — a LENTE DO DADO.** Na 093-B, 4 lentes + red team + juiz de confirmação olharam o CÓDIGO e
o GUARDA e aprovaram. A auditora externa reconstruiu o DATASET que o produto ia gerar sobre 1.851 sessões
reais e achou que a "variante" era um histograma de mensagens (`RRRR 217 · RR 200 …`) e que 40,8% dos
documentos de sinistro nunca viravam evento. Nenhum dos dois é visível no diff: só no dado. A lente entra
no painel quando o outcome é número ou dataset — custa uma lente, e pega antes da rodada de conserto.

**Emenda B — PARES MÍNIMOS.** O guarda do detector fixava 17 frases e ficou verde com um defeito que
vetava ~9,5% das sessões: nenhuma frase era "sinistro genuíno COM palavra de venda ao lado". Uma lista de
casos sem o par adversarial (mesma superfície, veredito oposto) prova só o lado fácil. CLAUDE.md §9.5.

**Emenda C — conserto salvo completo.** Um `429` matou dois builders no meio de um refactor de
`claims_shadow.py` e a árvore ficou com `AttributeError` em toda importação. Custou a restauração por HEAD
e uma rodada. A regra é a mesma do commit atômico, escrita onde o builder lê.

**O que NÃO mudou, e por quê:** o teto de 3 rodadas; o painel máximo de 5 (a lente do dado substitui uma
lente de leitura, não soma); o juiz de confirmação (pegou o único defeito de conserto).
📊 Tamanho do protocolo: 21.546 → 21.867 bytes (teto 22.528).


---

## DIÁRIO DA v11.1 → v11.2 · 03/09/2026 · a economia de tokens, pedida pelo Founder

📊 **O problema medido:** a janela de 5h do plano acabou DUAS vezes no meio de uma SPEC (093-B ~06:30 e 094 ~10:40), e cada
vez custou ~3h parado e agentes mortos no meio de refactor. O harness devolve o gasto por agente: investigador 154 mil ·
aquecimento 153 mil · censo 203 mil · auditoria externa 245 mil · builder de conserto 264 mil · 4 lentes + red team ≈ 900 mil.
Uma SPEC CRÍTICO ≈ **3 milhões de tokens de subagentes**, sem contar o orquestrador.

**Onde o julgamento NÃO estava:** a auditoria externa achou 2 blockers que 5 frentes não viram — pela LENTE (o dado), não por
ser um agente a mais. O juiz de confirmação e a auditora liam o mesmo diff. Fundir os dois num agente fresco com missão dupla
mantém as duas perguntas e tira ≈200 mil tokens. Lentes 4→3 no CRÍTICO e 3→2 no PADRÃO: na 088 e na 093-B, 2 dos blockers de
cada painel foram achados por 2+ lentes — a sobreposição paga uma lente.

**O que muda e o que se espera (💭 estimativa, a medir na 094 e na 095):** entre 35 e 45 por cento menos tokens por SPEC, com
perda irrisória no PADRÃO (a confirmação mecânica reroda guardas e mutações, que é o que o juiz de confirmação fazia de útil) e
perda pequena no CRÍTICO (uma lente a menos; a do DADO fica). O que NÃO se corta: mutação, gate zero, aquecimento (nota 74 →
15 emendas na 094 com 153 mil tokens: o melhor custo-benefício da leva), desenhista antes do código.

**Regra nova que decide sozinha:** estourou o orçamento → menos LENTES, nunca menos MUTAÇÃO. E a sessão de 5h começa pelo laço
mais longo (o builder serial), para não morrer no meio dele.
📊 Tamanho do protocolo: 21.867 → 22.498 bytes (teto 22.528).
