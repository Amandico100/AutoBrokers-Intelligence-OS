# PROTOCOLO AUTOBROKERS AAA

> **Como se monta e se governa uma equipe de agentes no AutoBrokers.**
> Não diz **o que** construir — isso é a SPEC. Diz **como construir, julgar e
> autorizar a entrega**, e **quando parar**.
>
> **v10 · 30/08/2026** · vale para toda SPEC, execução, ideia, incidente e agente.

---

## 0. A REGRA DE UMA LINHA

> ## Nada entra como pronto sem sobreviver a uma cadeia independente de provas.
> ## E nada trava o projeto por um defeito que não muda o produto.

---

## 0.1 ⛔ ESTE PROTOCOLO É LEI, E ELE SE CARREGA SOZINHO

> ### 🔴 Nenhuma execução começa sem que este documento esteja no pacote.

⚠️ **A v10 nasce de uma auditoria que mediu por que a v9 não rodava** — e a causa
não era desobediência. Era **omissão de uma linha**:

```
📊 092 e 093    o prompt mandava LER o protocolo   →  o painel RODOU     2 de 2
📊 087·090·086·089   o prompt NÃO mandava          →  não rodou          0 de 4
```

🔴 **A §1 listava seis itens que o pacote precisa carregar — e esquecia de si
mesma.** Um prompt que obedecia a §1 com perfeição entregava um pacote **sem o
protocolo dentro**.

### O que isso custou, medido

```
COM PAINEL    47 achados · 22 defeitos de PRODUTO   →  23,5 por SPEC
SEM PAINEL    19 achados ·  0 defeitos de produto   →   6,3 por SPEC
                                                        3,7× menos
```

⚠️ **E a diferença não é de volume, é de CLASSE.** Sem painel, 17 dos 19 achados
eram *"guardas que não guardavam"* — defeito de teste. Com painel: vazamento
entre corretoras, resposta em dobro ao segurado, `RecursionError` derrubando o
webhook. **Defeito de produto.**

```
o painel custa    ~4% do relógio
a bateria custa    50% do relógio
```

### ⛔ As três linhas que tornam isto executável

```
1. TODO pacote de execução carrega este protocolo — §0, §1, §2, §3, §5.
   🔴 Sem ele, o agente NÃO COMEÇA. Ele pede.

2. TODO relatório de execução abre com o EXECUTION CARD (§0.2).
   🔴 Relatório sem card = SPEC não fechada.

3. Quem escreve o prompt de execução é responsável pelo item 1.
   ⚠️ Falhar aqui não é falha do executor. É de quem montou o pacote.
```

---

## 0.2 🔴 O EXECUTION CARD — dez linhas, antes de escrever código

**Toda execução começa cuspindo isto, e o Founder lê em vinte segundos:**

```
OUTCOME ..............  o que muda para quem usa
RISCO ................  0–8   (alcance + reversibilidade + frequência, §3)
SUPERFÍCIE ...........  0–3   (§3)
PISO APLICADO ........  qual, e por quê (§3.2)
UNIDADES .............  quantas, e quais
COESÃO ...............  quais ficam JUNTAS e por quê (§3.4)
PARALELISMO REAL .....  quantos escritores ao mesmo tempo — ou "nenhum"
TIME .................  os papéis que a conta pediu (§4)
REFERÊNCIA ...........  o artefato que o juiz vai ABRIR (§7)
GATES ................  o que precisa ficar verde
🔴 O ELO ..............  a afirmação-título liga A a B? Então MEDIU O ELO,
                        não só as pontas (§0.3)
FAIXA DE RELÓGIO .....  ex.: 1–2h  ·  🔴 faixa, nunca promessa
```

🔴 **Por que ele existe:** 📊 a conta do §3 foi executada **ZERO de seis vezes**
nas últimas SPECs — inclusive nas duas que rodaram o painel. Um passo
obrigatório com 100% de descumprimento **e sem gate** não é regra: é decoração.

⚠️ **E o card é o gate.** Em dez linhas o Founder vê, antes de começar, se o
agente vai abrir nove builders para mudar uma string — ou zero juízes para mexer
em `company_id`.

---

## 0.3 🔴 O ELO — duas medições certas não fazem uma causa certa

📊 **Acrescentado em 02/09/2026, depois que DUAS SPECs convertidas sob a v10
caíram no mesmo buraco — e nenhuma delas errou um número.**

```
SPEC-088   📊 "9 execuções completed"     ✓ exato
           📊 "zero produção há 7 dias"    ✓ exato
           🔴 ligadas por um `beat()` que NÃO DISPARA há meses

SPEC-091   📊 "4 de 10 não carregam o protocolo"   ✓ exato
           🔴 e a regra tinha DUAS metades. A segunda: 9 de 10
```

> 🔴 **As duas mediram as PONTAS. Nenhuma mediu o ELO.**

⚠️ **E isto é um defeito de nível novo, não uma recaída.** O defeito antigo era
*"o número está errado"* — 📊 a SPEC-087 afirmava `escalated = 4` quando eram
14+2. **Só se chega em "a causalidade não foi conferida" depois de parar de
errar o número.** É subir de patamar, e o patamar novo tem buraco próprio.

### A pergunta, e ela cabe em uma linha

```
minha afirmação-título é da forma "A acontece PORQUE B"?
   → eu medi A?      ✓ quase sempre sim
   → eu medi B?      ✓ quase sempre sim
   🔴 eu medi que B CHEGA em A?      ← este é o passo que ninguém dá
```

**Três formas do mesmo erro, todas vistas neste projeto:**

| forma | como aparece | como se pega |
|---|---|---|
| **código morto** | a linha culpada existe, e um `return` acima dela impede que rode | rode o caminho, ou leia da linha 1 da função até ela |
| **meia regra** | a regra é `A E B`, e só `A` foi contado | conte cada cláusula separada, sempre |
| **fonte de ontem** | o número é certo, mas quem escreve mudou de tabela | pergunte *"quem É o escritor HOJE"*, não *"quem era"* |

🔴 **E o corolário, que é o mais caro:** um conserto sobre um elo não conferido
**fica verde com o produto idêntico.** 📊 Na SPEC-088, o D1 consertaria um
`beat()` inalcançável: gate verde, card mentindo igual, e a SPEC fechada.

---

## 1. 🔴 A DIETA — a primeira regra, porque é o maior custo medido

```
🔴 O AGENTE RECEBE UM PACOTE, NUNCA O CANON.

   🔴 ESTE PROTOCOLO — §0, §1, §2, §3, §5 — SEMPRE, e é o primeiro item
   + o contrato da unidade
   + as interfaces que ela toca
   + as regras invioláveis PERTINENTES, por número
   + os arquivos, por caminho
   + a REFERÊNCIA que o juiz vai abrir (§7)
   + os gates
   + as pendências POR NÚMERO — 🔴 nunca o `PENDENCIAS.md` inteiro
```

> ⛔ **A primeira linha é nova na v10, e ela é a razão da v10 existir.**
> 📊 A lista antiga tinha seis itens e **esquecia de si mesma**: um pacote
> montado com perfeição saía **sem o protocolo dentro** — e foi exatamente o que
> aconteceu em 4 das 6 últimas SPECs. Ver §0.1.

⚠️ **A prática já fazia isso e a regra não.** Os prompts de execução deste projeto
já estreitam a leitura a seis itens e a cinco IDs. **Agora é regra, e o
`CLAUDE.md` §2 passa a ser o ÍNDICE de onde as coisas estão — não uma lista de
leitura obrigatória.**

```
🔴 `PENDENCIAS.md` se parte em dois:
      PENDENCIAS.md            só as abertas
      PENDENCIAS-FECHADAS.md   arquivo, fora do bootstrap
🔴 Nenhum documento novo entra no bootstrap sem que outro saia ou encolha.
```

📊 **Por que isto é a §1:** 865 KB por agente, por sessão, crescendo 31% em quatro
dias. **Nenhum outro item deste protocolo custa tanto.**

---

## 2. 🔴 O TESTE DO PRODUTO — decide se algo é blocker

```
Se eu consertar isto, muda UM BYTE do que chega:
   · ao SEGURADO       mensagem, protocolo, prazo, cobrança
   · à CORRETORA       tela, alerta, decisão, e o relatório que o PRODUTO gera
                       🔴 nunca o relatório de execução da SPEC
   · ao BANCO          dado gravado, estado, integridade
   · ou à SEGURANÇA    acesso, isolamento, vazamento

SIM  →  BLOCKER. Conserta, e o laço continua.
NÃO  →  PENDÊNCIA. Registra, e SEGUE.
```

⚠️ **O contrário é proibido.** *"Isto é pequeno"* não é argumento.

**Quem drena:** toda SPEC que começa fecha ou re-justifica as pendências que ela
toca — `FECHADA` (com a prova) · `CONTINUA` (com o que destrava, novo) · `MORREU`.

---

## 3. DUAS CONTAS, NÃO UMA

🔴 **O RISCO diz SE precisa de juiz. A SUPERFÍCIE diz DE QUANTAS PESSOAS.**

```
ALCANCE          ninguém 0  ·  a corretora 2  ·  o SEGURADO 3

REVERSIBILIDADE  🔴 mede o que FICA depois de desfazer o gesto
                 desfez e não sobrou nada ......... 0
                 sobra dado, estrutura ou estado .. 2
                    ⚠️ a linha no ledger de migration NÃO conta
                 saiu do prédio: mensagem, chamado,
                 portal, dinheiro ................. 3

FREQUÊNCIA       raramente 0  ·  toda semana 1  ·  TODO atendimento 2
```

⚠️ 📊 *"É só um commit"* descreve o **gesto**. O `revert` é trivial; o que ele
deixa para trás, não.

```
SUPERFÍCIE  0  uma decisão, num lugar, e eu SEI APONTAR o lugar
            1  um comportamento, em alguns lugares que eu listo
            2  vários comportamentos, ou uma peça nova
            3  território que ninguém mapeou — ou um lote nunca julgado junto
```

> **"Consigo apontar TODOS os lugares que isto muda?" Não → SUPERFÍCIE 3.**

#### 🔴 Dois "não saber" — só um é SUPERFÍCIE

```
NÃO SEI ONDE PEGA           → SUPERFÍCIE. Mais gente: alguém vai ver.
NÃO SEI SE O MODELO OBEDECE → 🔴 é PROVA. Mais gente não torna LLM previsível.
```

Texto que instrui modelo pontua pelos **comportamentos que dirige**, e sai com
uma obrigação a mais: **mostrar o modelo fazendo.**

#### O LOTE paga UMA passada de enquadramento

O entregável é **a lista das unidades, cada uma já pontuada**. A SUPERFÍCIE 3 do
lote **não se herda**.

> **UNIDADE = a menor coisa que dá para ENTREGAR e PROVAR sozinha.**

### 3.1 A tabela — cada célula por extenso, de propósito

```
                     SUPERFÍCIE 0        SUPERFÍCIE 1–2       SUPERFÍCIE 3
 ────────────────────────────────────────────────────────────────────────
  RISCO 0–1          🔴 NINGUÉM          builder             builder
                       faz e pronto      juiz                juiz
                                                             verificador
 ────────────────────────────────────────────────────────────────────────
  RISCO 2–5          builder             builder             builder
                     juiz                juiz                juiz
                                         verificador         verificador
                                                             investigador
                                                             desenhista da prova
 ────────────────────────────────────────────────────────────────────────
  RISCO 6+           builder             builder             builder(es)
                     JUIZ DA             juiz da superfície  investigador
                       SUPERFÍCIE        verificador         desenhista da prova
                                         desenhista da prova verificador
                                                             juiz por superfície
                                                             RED TEAM
                                                             integrador
                                                             JUIZ FINAL fresco
```

⚠️ **Os rótulos são TÍPICOS. Se o rótulo e a soma discordarem, a soma vence.**
⛔ **A célula "ninguém" dispensa o JUIZ. Nunca o passo ② da §5.**

### 3.2 🔴 O PISO — por EFEITO, nunca por tipo de arquivo

```
RISCO 6 no mínimo, independente da conta:
 · qualquer coisa que ENVIE      mensagem, acionamento, chamado, cobrança
 · migration que ALTERA DADO, ESTRUTURA, TRAVA ou QUEM PODE LER
   ⚠️ a ÚNICA isenção é o COMMENT. Índice e GRANT disparam.
 · autenticação, sessão, ou o filtro `company_id`
 · ler de uma corretora e escrever noutra
```

### 3.3 A conta vale para MUDANÇA, não para INVESTIGAÇÃO

```
CONSULTA PONTUAL  "onde está X?" · "o que faz Y?"        → dispensado
VARREDURA         "isto funcionou?" · "serve para nós?"  → MODO INVESTIGAÇÃO
```

### 🔴 3.4 A COESÃO — o que decide se dá para paralelizar ESCRITA

⚠️ **Arquivos diferentes NÃO significam trabalhos independentes.** Dois agentes
podem tocar arquivos separados que compartilham a mesma interface, o mesmo tipo,
o mesmo contrato — e aí o que se ganha em paralelo se perde em reconciliação.

```
🔴 ALTO ACOPLAMENTO   →  MESMO escritor, em sequência
   BAIXO ACOPLAMENTO  →  candidato a paralelo
   ARQUIVO-HUB        →  UM dono por vez, sempre
```

**Como medir, em três perguntas — e sem construir ferramenta:**

```
1. as unidades tocam a MESMA interface, tipo ou contrato?     → juntas
2. alguma delas REDEFINE algo que a outra consome?            → juntas
3. o `OWNS` de cada uma é realmente disjunto?                 → se não, juntas
```

⛔ **Se mapear isso custar mais que fazer a tarefa, não mapeie.** Tarefa pequena
continua pequena — é a §12.

📊 **Por que a regra existe:** na SPEC-085 os commits de fase tocavam
repetidamente o mesmo `dispatch_router.py`. **Paralelizar escrita ali teria sido
pior**, e a medição daquela SPEC virou proibição universal. 🔴 **A v10 desfaz a
generalização sem desfazer a lição:** aquele caso continua serial; um caso com
partições realmente disjuntas, não.

> **PARALELIZE O QUE TEM POUCA CONVERSA. MANTENHA JUNTO O QUE TEM MUITA.**

---

---

## 4. OS PAPÉIS — só existem os que a conta pediu

```
🎯 ORQUESTRADOR   faz as contas, monta o time, controla o laço, REGISTRA
🔍 INVESTIGADOR   lê antes de qualquer edição. 🔴 não escreve
📐 DESENHISTA     escreve os testes. 🔴 quem faz a prova não faz a resposta
🔧 BUILDER        implementa
⚙️ VERIFICADOR    🔴 é PASSO do laço, não papel que a conta convoca
⚖️ JUÍZES         um por SUPERFÍCIE DE FALHA. 🔴 contexto fresco
🗡️ RED TEAM       missão: FAZER QUEBRAR. A partir de RISCO 6 × SUP ≥1
🧩 INTEGRADOR     3+ unidades no mesmo lote
🏁 JUIZ FINAL     contexto limpo, olha o sistema, não o diff
```

### O verificador mecânico — a lista curta não basta

```
build · testes · lint · tipos · migrations · regressão
⛔ 📊 essa lista é a que deixou o produto 1h40 no chão com tudo verde.
🔴 Mexeu em `app/`, `middleware.ts`, `next.config.js` ou env:
   npm run test:rotas-montam + next start + UMA requisição a /api/…
   ⚠️ arquivo estático responde 200 com o roteador morto
🔴 "migrations" é a `MIGRATIONS-AUTHORITY.md`, não a `schema_migrations`:
   o ledger MENTE. O VERIFY confere o OBJETO no banco.
```

### 🔴 A regra que mais paga, e custa uma frase

> **Todo subagente reporta o que vir FORA do próprio escopo.**

---

## 5. O LAÇO — 🔴 um painel, e ele julga CÓDIGO

```
① o builder entrega
② o VERIFICADOR MECÂNICO roda   →  FAIL aqui não vai a juiz, volta direto
③ 🔴 O PAINEL: N lentes DE UMA VEZ, cegas entre si, contexto limpo
④ o ORQUESTRADOR funde e aplica o TESTE DO PRODUTO a CADA achado
⑤ conserta TUDO junto
⑥ 🔴 UM JUIZ NOVO confirma — porque CONSERTO CRIA DEFEITO
```

### 🔴 5.1 · O JUIZ JULGA CÓDIGO. É a regra mais cara do documento.

📊 **Medido:** quando o painel rodou **depois do código**, comprou **1.008 linhas
de conserto de produto**. Quando rodou **antes, sobre um documento**, comprou
**610 linhas de documento e zero de código.**

```
⛔ NÃO se monta painel de juiz sobre uma SPEC.
✅ O painel roda sobre o DIFF, o teste rodando, o banco.
```

### 🔴 5.2 · Então quem julga a SPEC? O AQUECIMENTO DO EXECUTOR.

```
o executor recebe a SPEC + um questionário de 12–15 perguntas
  🔴 várias com resposta óbvia E ERRADA, medidas de propósito
  🔴 DUAS afirmam algo FALSO com todas as letras, assinadas por quem manda
  🔴 e uma pede: "liste o que você NÃO entendeu" — "entendi tudo" reprova
       ↓
o orquestrador corrige o que estiver torto, e libera
```

📊 **Por que vale mais que voltas de juiz:** na SPEC-083, oito voltas em série
levaram 4h13, e o commit final registra que *"o executor achou o que oito rodadas
de juiz não acharam"*. Na SPEC-085, o aquecimento achou **cinco erros do autor** —
incluindo `pytest tests/` morto, que três voltas não viram.

> **Quem vai ter de viver com a resposta lê melhor que quem só julga.**

### 🔴 5.3 · Nunca a mesma lente duas vezes

📊 Dois juízes de contexto limpo, o mesmo artefato: **sobreposição de achados
praticamente ZERO.**

⛔ **O JUIZ RETOMADO ESTÁ PROIBIDO.** 📊 Ele deu a nota **mais alta** das três
voltas (+11 sobre a anterior, **25 acima** do juiz fresco) e deixou passar quatro
instruções que quebrariam produção — **uma na seção que ele mesmo elogiara.**
Ele julga a resolução dos próprios achados. **Não é só custo: é nota falsamente
alta que autoriza entregar.**

### As portas

```
✅ o painel libera
📋 sobraram só pendências  →  registra e entrega
🛑 3 rodadas de painel     →  CLASSIFICA (não é parada):
      é uma das oito do CLAUDE.md §10?
      SIM → para e registra   ·   NÃO → 🔴 entrega o que passou e AVANÇA
```

🔴 **Teto: 3 rodadas de PAINEL. Ponto — mudando o produto ou não.** Uma quarta é
decisão do Founder, escrita no relatório.

### 🔴 O detector de achado repetido

```
≥60% dos achados da rodada N são os mesmos da N−1?
   →  NÃO é teimosia do juiz. Confira A ÁRVORE primeiro.
```

📊 Um juiz reprovou duas vezes o mesmo defeito e **estava certo: o arquivo tinha
voltado.** Sem esta regra, culpa-se a lente.

```
⛔ NUNCA: afrouxar a régua · alterar o teste para passar · declarar pronto
   por cansaço. Nenhuma das três é uma porta.
```

---

## 6. O JUIZ

```
RECEBE   a SPEC · o contrato · a referência · 🔴 O ARTEFATO REAL
NUNCA    a narrativa do builder · o esforço · "está funcionando" · o resumo
```

```
Presuma FAIL até existir evidência de PASS.
Não premie esforço. Não considere intenção. Não aceite "parece funcionar".
Cite arquivo, linha, comando, saída ou consulta em CADA conclusão.
🔴 Se estiver bom, diga que está bom. Um juiz que precisa achar defeito
   para se justificar É o defeito que este protocolo existe para matar.
```

**A forma:** VEREDITO · BLOCKERS (com o teste do produto) · PENDÊNCIAS ·
EVIDÊNCIA · MAIOR LACUNA · PRÓXIMA AÇÃO · CONFIANÇA e o que ficou por medir.

```
⚖️ O JUIZ CLASSIFICA    blocker ou pendência
🎯 O ORQUESTRADOR REGISTRA, e a decisão final é dele
🔴 REBAIXOU UM BLOCKER? a discordância vai ESCRITA no relatório
🔴 NÃO SE REBAIXA: segurança, isolamento, P0/P1 do CLAUDE.md §10
```

### 🔴 PRESCRIÇÃO DE JUIZ NÃO É MEDIÇÃO

```
O juiz entrega a MEDIÇÃO junto com o achado.
O executor REPRODUZ antes de aplicar — e devolve com o número se não bater.
O juiz roda o padrão na ferramenta que vai usá-lo.
```

⚠️ **Corta os dois lados.** O executor não desqualifica um achado chamando-o de
prescrição: ele tenta reproduzir e mostra o resultado.

---

## 🔴 6.1 A AUDITORIA EXTERNA — quem olha de fora vê o que o laço não vê

📊 **Medido duas vezes, e nas duas o laço interno tinha rodado:**

```
SPEC-093   o painel rodou, achou 22 defeitos
           🔴 e uma auditoria EXTERNA achou depois uma REGRESSÃO que ele não viu:
              o clique da atendente apagava o caso da única fila que existe

SPEC-089   a SPEC foi escrita com cuidado
           🔴 e a auditoria externa derrubou QUATRO afirmações dela,
              inclusive um orçamento de "5 horas" que eram 9m59
```

**A diferença não é competência. É posição.** O painel julga **durante**, com o
contexto do trabalho. A auditoria externa julga **depois**, sobre o resultado, e
sem saber o que foi difícil.

### Quando ela é obrigatória

```
🔴 RISCO 6+  ou  qualquer coisa que o segurado alcança
🔴 toda SPEC que mexe em company_id, migration, envio ou Core
```

### Como ela funciona

```
✅ contexto NOVO, que não viu a execução
✅ recebe: a SPEC · o código pronto · a referência (§7)
⛔ NÃO recebe: o relatório do executor, nem por que algo foi difícil
🔴 e a missão é: "ache um defeito real que o executor não achou"
```

⚠️ **Ela NÃO substitui o painel** — 📊 o painel achou 58 defeitos nas seis SPECs;
a auditoria externa achou 3. **Ela pega uma classe diferente:** o que o próprio
conserto criou, e o que todo mundo por dentro passou a achar normal.

---

## 7. A REFERÊNCIA — o que substitui "faça excelente"

```
1. INSPECIONÁVEL      o juiz ABRE, RODA ou MEDE. Se só imagina, é adjetivo.
2. UM PONTO ESPECÍFICO, nunca o produto inteiro
3. A INTERNA VENCE A EXTERNA — 🔴 mas a MEDIANA do que passou no gate,
   nunca o outlier: copiar o topo produz alvo que ninguém alcança
4. UMA POR DIMENSÃO — e cada uma tem NOME e CAMINHO na tabela abaixo
```

## 🔴 7.1 · AS REFERÊNCIAS DO AUTOBROKERS — abra, rode, compare

⚠️ **Esta tabela é a v10 inteira em uma peça.** 📊 A auditoria de 30/08 mediu que
a §7 nomeava **zero artefatos abríveis**: *"as conversas-ouro"* tinha **uma
ocorrência no repositório — esta própria linha**. E `0 de 9` relatórios de
execução citavam referência.

> **O projeto tinha referências melhores que quase qualquer repositório, e o
> protocolo não apontava para nenhuma. Não faltava construir: faltava NOMEAR.**

> ⚠️ **Este protocolo NÃO é de atendimento.** Ele governa **qualquer** entrega:
> uma aba nova no dashboard, uma feature, uma SPEC, um refactor, um incidente.
> A tabela abaixo tem duas metades por isso.

### A · TRABALHO GERAL — vale para qualquer entrega

| dimensão | 🔴 a referência, por caminho | como o juiz compara |
|---|---|---|
| **UI / design** | `docs/canon/DS-001-design-brief.md` **§5** | 📊 1.555 linhas, e a §5 compara com **ChatGPT · Claude · Claude Routines · Connectors** — é a referência EXTERNA deste projeto, e ela existe |
| **multi-tenant** | `CLAUDE.md` §7 + teste com **dois tenants reais** | o filtro no código, não a RLS |
| **migration** | `docs/canon/MIGRATIONS-AUTHORITY.md` | APPLY · VERIFY · ROLLBACK escritos ANTES de rodar |
| **um guarda serve?** | `CLAUDE.md` §9.3 + a **linha de controle** | prove que ele CONSEGUE ficar vermelho |
| **o build sobe?** | `CLAUDE.md` §9.1 | `next start` + **uma requisição a `/api/…`** — arquivo estático responde 200 com o roteador morto |
| **o número é medido?** | `CLAUDE.md` §12.1 | 📊 medido tem consulta e data · 💭 ilustrativo nunca é citável |

⛔ **E o que NÃO temos para trabalho geral — declarado, não fingido:**

```
🔴 TELA DE REFERÊNCIA    nenhuma tela do dashboard é designada como padrão.
                         O DS-001 diz como PENSAR; nenhuma diz "está bom assim".
🔴 GUARDA DE UI          nenhum. Os testes com "tela" no nome são todos de URA.
   API                   não existe arquivo OpenAPI no repositório
   SLO                   não existe alvo de latência
   OWASP                 citado, nunca aplicado a um julgamento
```

⚠️ **Nessas cinco, a regra do §7 vale ao pé da letra:** sem referência
inspecionável, a dimensão é **"não avaliada"** — nunca "aprovada". 🔴 **E a
primeira delas é barata:** designar uma tela como padrão custa uma linha, e
transforma *"ficou bonito?"* em *"chega perto daquela?"*.

### B · TRABALHO DE ATENDIMENTO — quando a entrega toca corredor ou segurado

| dimensão | 🔴 a referência, por caminho | como o juiz compara |
|---|---|---|
| **corredor / rota** | `backend/scripts/medir_rota.py --com-espelho` | roda e compara **número contra número** |
| **a rota de referência** | 📊 `allianz/auto/guincho` = **76/76 AAA(76)** | a rota nova chega perto? |
| **atendimento ponta a ponta** | `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py` | 📊 a sessão real `b2bf40e7`, turno a turno |
| **conversas-ouro** | `backend/tests/test_golden_do_eletricista.py` | 📊 **10 casos** lidos do banco de produção |
| **telas reais de URA** | `backend/tests/corpus/telas_reais/` | 📊 **16 arquivos · 4.279 linhas · 10 seguradoras** |

### 🔴 C · COMO USAR UMA REFERÊNCIA DE FORA — repositório, produto, concorrente

**É permitido, e o projeto já faz.** A regra 3 subordina, não proíbe:

```
existe referência INTERNA?   →  ela vence, e a externa vira complemento
não existe?                  →  a externa É a referência, e vai no relatório
```

⛔ **Mas ela precisa passar nas mesmas duas exigências:**

```
1. INSPECIONÁVEL   o juiz consegue ABRIR o repositório, a tela, o produto.
                   "o padrão do mercado" não é referência — é adjetivo.
2. UM PONTO        "como o Linear faz o estado vazio de uma lista",
                   nunca "faça no nível do Linear".
```

📊 **Exemplo que já existe neste projeto:** o `DS-001` §5.1 não diz *"seja bom
como o ChatGPT"*. Ele nomeia **para que** cada referência serve, item a item.
**É essa a diferença entre referência e elogio.**

## 🔴 7.2 · O caso que prova por que isto importa

📊 18/08/2026, no teste do eletricista:

```
12:23:43  ←  "O que aconteceu? 1-Casa sem energia 2-Curto circuito"
              <<< 2 MINUTOS E 22 SEGUNDOS DE SILÊNCIO >>>
12:26:05      o Founder clicou "1" do próprio celular
```

A causa, no docstring do arquivo: *"criei o passo `o_que_aconteceu` exigindo um
slot que NADA no produto preenchia. Passo que exige slot que ninguém preenche
não responde e não avisa — fica calado."*

> 🔴 **Uma conversa-ouro reexecutada teria parado naquele turno.**
> E a prova é que **o conserto foi construir a referência**: mapear a sessão real
> turno a turno. **Pagamos o defeito e só então fabricamos o instrumento que o
> teria pego.**

```
🤖 O AGENTE PROPÕE, junto com a conta, ANTES de montar time
🧑 O FOUNDER CONFIRMA
🔴 SE ELE NÃO RESPONDER, NÃO SE TRAVA: segue com "proposta, não confirmada",
   escrita no relatório. Se o alvo mudar, a rodada se repete contra o novo.
🔴 Sem referência inspecionável, a dimensão vira "não avaliada", nunca "aprovada"
```

⚠️ **Referência OBSERVADA registra o que foi feito, não o que se deve fazer.**
📊 Os humanos responderam *"sim"* a *"continuar com o CPF da conversa anterior?"* —
copiar a maioria abriria o chamado no CPF errado. **Toda tela de identidade,
dinheiro ou escolha-entre-existente-e-novo precisa de julgamento humano.**

---

## 8. OS MODOS

| modo | a conta governa? | o que dimensiona |
|---|---|---|
| 🧭 **INVESTIGAÇÃO** · ideia, auditoria, mapeamento, medição | ❌ (§3.3) | largura, teto 4 frentes |
| 📝 **SPEC** | ✅ do trabalho que ela MANDA fazer | as duas contas |
| 🔨 **EXECUÇÃO** | ✅ por unidade | as duas contas |
| 🤖 **AGENTE** · Central, auto-evolução, destilação | ✅ + três travas | as duas contas |
| 🚨 **INCIDENTE** | ❌ | elenco mínimo, juiz adiado |

### 🧭 INVESTIGAÇÃO — dois elencos

```
IDEIA       INVESTIGADOR (o que é · 🔴 o que MUDOU em 3 meses)
            ANALISTA (o que isto substitui, melhora ou DUPLICA — CLAUDE.md §5)
            CÉTICO (por que NÃO: custo, dependência, o que quebra)
            JUIZ DO VALOR (quantos atendimentos/mês, e em quanto)
            SAÍDA: FAZER AGORA · DEPOIS (com o que destrava) · NÃO FAZER
            🔴 "não fazer" é resultado legítimo

AUDITORIA   MEDIDOR (todo número com a consulta E a linha de controle)
            CÉTICO DA MEDIDA (a consulta mede o que a frase diz?)
            HISTÓRICO (que SPEC ou commit produziu este estado)
            JUIZ DO RISCO (o que quebra se ficar; o que quebra se mudar)
            🔴 SAÍDA: o estado · o que está quebrado · o que destrava
               · e O QUE FICOU POR MEDIR — sem essa linha não é auditoria
```

### 📝 SPEC

```
INVESTIGADOR  mede o estado. 🔴 todo número nasce de uma consulta
DESENHISTA    escreve os gates ANTES do texto
BUILDER       escreve a SPEC
🔴 AQUECIMENTO (§5.2) no lugar do painel — e a SPEC vai para o executor assim
   que passar nele. Não se poli documento enquanto ninguém escreve código.
```

🔴 **O defeito característico, em seis versões seguidas:** a correção entra no
corpo e **não sobe para o gate, o relatório nem o resumo**. **Depois de cada
reescrita, `grep` por cada conceito que mudou de definição. Releitura nunca achou
nenhum.**

### 🔨 EXECUÇÃO

```
Time pelas duas contas, por unidade.
🔴 A ESCRITA É DE UM SÓ. Builders paralelos no mesmo módulo custam mais em
   integração do que ganham em paralelismo.
   📊 Aqui o acoplamento é extremo: 4 de 4 commits de fase da SPEC-085 tocaram
   `dispatch_router.py`. Particionar era impossível, não malfeito.
   O grafo sai de `git log --name-only | sort | uniq -c`.
🔴 A integração é SERIAL, e a regressão roda depois de CADA merge.
```

### 🤖 AGENTE — o mais perigoso, porque roda sem ninguém olhando

```
1. TETO DE VOLTAS DURO, contado e registrado
2. TETO DE CUSTO por execução, declarado antes
3. O QUE ELE MUDA É REVERSÍVEL E FICA REGISTRADO
```

### 🚨 INCIDENTE — a lentidão É o dano

```
🔴 A conta NÃO se aplica: ela pontuaria 8 e convocaria red team com o
   produto no chão.
ELENCO: 🔧 quem conserta · 👁️ quem observa o EFEITO — uma rota que EXECUTA
   CÓDIGO responde? nunca um arquivo estático
🔴 O CONSERTO É REVERSÍVEL POR CONSTRUÇÃO: flag, revert, ou desligar.
   Se o conserto mais rápido é irreversível, ele é a segunda queda.
🔴 O JUIZ É ADIADO, não dispensado: vem no post-mortem, e julga o conserto
   E a causa.
```

---

## 9. 🔴 A LICENÇA DE AUTONOMIA — proibir a parada não basta

```
① O TESTE DO PRODUTO (§2)?          NÃO muda → PENDÊNCIA, e SEGUE
② Uma das oito do CLAUDE.md §10?    NÃO → não é motivo de parada
③ Precisa da MÃO do Founder?        SIM → 🔴 CAIXA DO FOUNDER, e SEGUE
```

> **Só para se os três derem SIM — e o próximo bloco for IMPOSSÍVEL, não incômodo.**

### 🔴 A REGRA DOS 30 MINUTOS

```
≤30 min E ≤2 arquivos E sem decisão a tomar  →  CONSERTA, e anota
qualquer outra coisa                          →  PENDÊNCIA
⛔ Se exige DECIDIR algo, não cabe. Sem exceção.
```

⚠️ **O critério não é "é importante?" — quase tudo é. É "cabe agora sem me tirar
do bloco?"**

### 🔴 9.1 O VALOR MARGINAL — quando o resto não muda o produto

**Depois de cada rodada, classifique o que sobrou:**

```
🔴 MATERIAL — continua
   segurança · isolamento entre corretoras · integridade de dado
   efeito colateral errado · Core · critério de aceite não provado
   regressão · falha real de serviço · evidência que falta para dizer PASS

⛔ NÃO MATERIAL AGORA — vira PENDÊNCIA e a execução AVANÇA
   estilo · micro-refactor · nome melhor · abstração mais bonita
   documentação que ninguém precisa para executar
   dívida sem efeito hoje · preferência de quem julga
```

> **A execução não ganha crédito por quantidade de lapidação.**

🧑 **É a preferência do Founder, escrita como regra:**

```
2h → 93/100 sem defeito material
   é MELHOR que
24h → 95/100 comprado com polimento

MAS

6h → 99/100 fechando risco real no Core
   é MELHOR que
2h → 85/100 deixando fragilidade estrutural
```

### 🔴 9.2 A FAIXA DE RELÓGIO, e o PORTÃO DO "POR QUE CONTINUAR"

O EXECUTION CARD (§0.2) declara uma **faixa**, nunca uma promessa: `1–2h`, `3–5h`.

⚠️ **Estourar a faixa não para nada automaticamente.** O que ela obriga é
responder, por escrito:

```
🔴 POR QUE CONTINUAR?
   o que ainda falta ·  que risco isso fecha
   que gate isso fecha ·  que evidência falta
```

**Resposta boa, e a execução segue:**
> *"Estamos em 4h15 porque achamos vazamento entre corretoras reproduzível.
> Falta corrigir a query e repetir com dois tenants. É blocker."*

**Resposta ruim, e vira pendência:**
> *"Tudo passa, mas estou refatorando as interfaces para ficarem mais elegantes."*

### 🔴 9.3 ATIVIDADE NÃO É PROGRESSO — o travamento sem avanço

📊 A SPEC-084.1 custou **31,9 horas** e produziu **151 linhas de produto por
hora** — contra 765 e 1.028 das SPECs recentes. **O agente estava ocupado o tempo
todo.**

**Os sinais, e bastam dois:**

```
o MESMO blocker em duas rodadas, sem evidência nova
a mesma hipótese repetida com outras palavras
nenhum gate mudou de estado
patch sendo feito e desfeito
a discussão cresce e o artefato não muda
```

**Quando acontecer:**

```
1. PARE o laço — não tente de novo
2. registre: o que está PROVADO · o que já se tentou · por que falhou
3. abra CONTEXTO FRESCO
4. troque a ESTRATÉGIA, não só o executor
```

⛔ **Travamento NUNCA transforma FAIL em PASS.** Ele troca o caminho, nunca o
veredito.

### 📋 A CAIXA DO FOUNDER

Uma seção do relatório que o executor **vai acrescentando**. ⛔ **Nunca se para
para entregar uma linha dela.** Cada item: **o que é · o que ele faz · o que
custa esquecer · bloqueia? (quase sempre NÃO).**

> **A caixa troca TRÊS paradas por UMA entrega.**

---

## 10. 🔴 A MECÂNICA — mesmo trabalho, metade do relógio

**Nada aqui muda o que se julga. Muda quanto custa julgar.**

```
🔴 UM ÚNICO `agent type` PARA TODO O PAINEL, variando só o PROMPT.
   Dois agentes só compartilham prefixo de cache com o MESMO modelo, effort,
   agent type, tools, schema e diretório. Um arquivo de agente por lente zera
   o compartilhamento: cada juiz reprocessa tudo do frio.
   ⚠️ A independência mora na INSTRUÇÃO, não no system prompt.

🔴 O PAINEL RODA NO DIRETÓRIO PRINCIPAL, SEM WORKTREE.
   O cache é escopado por diretório, e isso INCLUI worktrees. Juiz é read-only:
   não há escrita para isolar. Worktree só para quem ESCREVE.

🔴 `subagentPromptCacheTtl: "1h"` em `.claude/settings.json`.
   Todo subagente cai no balde de 5 MINUTOS enquanto a conversa principal tem
   1h. Num ciclo de horas, toda rodada depois da primeira nasce fria.

🔴 FORK para os AUXILIARES DO EXECUTOR — ele herda o cache do pai.
⛔ NUNCA fork para juiz: ele veria tudo o que o executor pensou.
   A fronteira fork/subagente é a mesma do julgamento.

⛔ NÃO trocar `/model` nem `/effort` no meio da sessão — os dois fazem parte
   da chave de cache, e trocar zera o histórico inteiro.
```

### 🔴 A bateria de mutação toma trava

📊 `verificar_mutacoes.py` **copia** o arquivo, muta, roda e **restaura da cópia**.
Com juiz e executor na mesma árvore, uma cópia feita antes de uma edição a
**apagou depois — sem erro, sem diff, sem aviso.**

```
🔴 A bateria roda em WORKTREE PRÓPRIO, ou toma lock exclusivo da árvore.
⛔ É pré-condição de qualquer paralelismo de escrita: sem ela, medir apaga.
🔴 Restaurar é POR CÓPIA, nunca por `git checkout`:
   `git diff --quiet` diz "idêntico" sobre arquivo que nem rastreia.
```

### 🔴 A BATERIA MECÂNICA é o maior sumidouro medido — e o conserto tem ordem

📊 **TRÊS medições da mesma suíte, no mesmo dia, na mesma máquina, mesmo resultado
(`418 passed, 45 xfailed`):**

```
19m01  ·  16m26  ·  14m46        média 16m44,  amplitude ±13%
```

⚠️ **E o primeiro número sozinho me fez escrever "variação de 28%" — que era a
diferença entre DOIS pontos, não a dispersão.** Com três, a leitura honesta é uma
**faixa**, e nenhum ponto isolado a representa.

🔴 **É a §6 outra vez, e agora contra mim:** um ponto não é uma medida. O `gate.yml`
registrava **13 min** assinados com 📊 e data — **fora da faixa inteira**, e citável.

⚠️ **E duas lentes discordaram aqui.** Uma extrapolou ~25 min de uma rodada morta no
timeout; a outra rodou até o fim e mediu 19m01. 🔴 **Venceu quem mediu** — é a §6
deste documento aplicada a ele mesmo.

```
📊 5 pushes tocando tests/ na SPEC-085  ×  19m01  =  95 min = 1,6 h
   sobre 405 min de execução  →  QUASE UM QUARTO da fase é esperar a suíte
```

🔴 **E ela não aparece em commit nenhum, porque acontece ENTRE eles.** É a maior
fatia isolada de desperdício medida — e o laço de juízes inteiro custou 59 min.

⚠️ **A suíte cresce a cada SPEC:** 322 testes em 24/08, **463** em 25/08. E o teto de
`TETO_SEGUNDOS = 120` × 272 scripts dá **9h de cauda no pior caso**.

### Onde a velocidade NÃO está

```
⛔ builders paralelos que ESCREVEM     o acoplamento aqui é extremo
⛔ agent teams para orquestrar          experimental; a espera pode travar
⛔ escalonador por caminho crítico      não há fila: a SPEC É a ordem
⛔ capar concorrência em 3–5            📊 nunca passou de 5 aqui
⛔ um terceiro eixo de "modo rápido"    a §3.1 já é uma grade de 9 rituais
```

---

## 11. 🔴 A TELEMETRIA — o protocolo mede a si mesmo

> **Este documento passou um mês exigindo medição de todo mundo e nunca mediu o
> próprio custo. As quatro lentes que produziram a v9 tiveram de reconstruir tudo
> de `git log`, porque não havia registro.**

**Toda execução escreve, na §0.1 do relatório:**

```
começou / terminou                    o relógio, não a sensação
🔴 tempo até a PRIMEIRA linha de código de produto     ← o número da v9
tempo em investigação · construção · painel · conserto
rodadas de painel                     e o que cada uma achou
achados por lente                     🔴 e quantos foram ACHADO ÚNICO
defeitos que o painel NÃO pegou       e quem os pegou
bytes que o agente teve de ler        🔴 o pedágio, por unidade
razão docs/código                     linhas de .md ÷ linhas de código
```

⚠️ **Sem estes números, "ficou mais rápido" é sensação.**

---

## 12. QUANDO NÃO SE APLICA

```
❌ célula "ninguém" da §3.1 — RISCO 0–1 × SUPERFÍCIE 0
❌ consulta pontual: "onde está X?", "o que faz Y?"
   ⚠️ varredura que vira conclusão NÃO é consulta pontual (§3.3)
❌ não substitui o CLAUDE.md: as regras invioláveis vencem
❌ não substitui a SPEC: ela diz O QUE, este diz COMO
❌ não é para ser lido inteiro toda vez. §1, §2, §3 e §5 resolvem 90%
```

🔴 **A exceção do Founder:** *"isto é mais importante do que parece"* → RISCO 6.
⚠️ **Não existe a contrária.** Quem tem pressa usa o **MODO INCIDENTE**, que é
declarado e fica escrito.

---

## 13. QUEM DECIDE, E DE ONDE VEIO

**O orquestrador, sozinho, sempre.** 🔴 **O Founder nunca precisa pedir. Se
precisar, o protocolo falhou.**

**Consenso de fora:** builder ≠ juiz, e juiz com contexto fresco · o contrato
antes do código · o juiz vendo o artefato real · a referência concreta em vez de
"faça bom" · hard gates antes de nota · risco e tamanho como eixos separados · a
mecânica de cache, fork e worktree (documentação de plataforma) · e *"dê ao
agente um MAPA, não um manual de mil páginas"*.

**Calibração deste projeto — pode não generalizar:** o teste do produto · os
quatro números e os cortes · o teto de 3 · *"todo subagente reporta fora do
escopo"* · *"grep por conceito, nunca releitura"* · o incidente com juiz adiado ·
**o aquecimento no lugar do painel da SPEC** · **e a §5.1: o juiz julga código.**

⚠️ **Quando um destes errar duas vezes seguidas, muda o número e registra por quê.**

📄 **As medições, o histórico das nove versões e a prova de cada regra:**
[`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md).
