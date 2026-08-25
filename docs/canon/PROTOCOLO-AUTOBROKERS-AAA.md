# PROTOCOLO AUTOBROKERS AAA

> **Como se monta e se governa uma equipe de agentes no AutoBrokers.**
> Não diz **o que** construir — isso é a SPEC. Diz **como construir, julgar e
> autorizar a entrega**, e **quando parar**.
>
> **v9 · 25/08/2026** · vale para toda SPEC, execução, ideia, incidente e agente.

---

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

## 0. A REGRA DE UMA LINHA

> ## Nada entra como pronto sem sobreviver a uma cadeia independente de provas.
> ## E nada trava o projeto por um defeito que não muda o produto.

---

## 1. 🔴 A DIETA — a primeira regra, porque é o maior custo medido

```
🔴 O AGENTE RECEBE UM PACOTE, NUNCA O CANON.

   o contrato da unidade
   + as interfaces que ela toca
   + as regras invioláveis PERTINENTES, por número
   + os arquivos, por caminho
   + os gates
   + as pendências POR NÚMERO — 🔴 nunca o `PENDENCIAS.md` inteiro
```

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

## 7. A REFERÊNCIA — o que substitui "faça excelente"

```
1. INSPECIONÁVEL      o juiz ABRE, RODA ou MEDE. Se só imagina, é adjetivo.
2. UM PONTO ESPECÍFICO, nunca o produto inteiro
3. A INTERNA VENCE A EXTERNA — 🔴 mas a MEDIANA do que passou no gate,
   nunca o outlier: copiar o topo produz alvo que ninguém alcança
4. UMA POR DIMENSÃO   segurança → OWASP · API → o contrato · UI → a tela
                      agente → as conversas-ouro · performance → o SLO
```

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

📊 **19m01**, medido até o fim em 25/08/2026 — `418 passed, 45 xfailed in 1141s`.
O `gate.yml` registrava **13 min** assinados com 📊 e data: **errado por 47%**.

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

⛔ **MAS A ORDEM DO CONSERTO NÃO É ÓBVIA, e invertê-la troca um problema de tempo
por um de PERDA DE DADO:**

```
1º  A TRAVA DA BATERIA (§10, acima).  📊 É a bateria rodando na árvore
    compartilhada que apagou dois consertos. Afinar QUANDO ela roda sem mudar
    ONDE ela roda troca lentidão por trabalho perdido.

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
