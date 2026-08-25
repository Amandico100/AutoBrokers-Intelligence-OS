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
