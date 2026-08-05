# A noite da destilação — 04/08/2026

> **A frase que resume:** 1.780 conversas viraram conhecimento em uma rodada, com
> custo zero de API para o pensamento. E vinte e sete leitores independentes, sem
> combinarem, apontaram para o mesmo buraco: **o que a corretora resolve bem, ela
> resolve por áudio — e o áudio não chega ao acervo.**

**Branch:** `feat/spec063-atendimento-canais` · **Commit inicial:** `20f72cf`
**Método:** plano MAX, 27 subagentes Opus 5, orquestração por pacotes de 70 conversas

---

## 1. O que foi feito

| | |
|---|---|
| conversas destiladas | **1.784** |
| pacotes | 27 · **zero reprovados** pelo validador |
| cartas escritas | **1.499** |
| custo de API para destilar | **US$ 0,00** — plano MAX |
| custo para indexar no RAG | 💭 ~US$ 0,003 (embeddings OpenAI, não Anthropic) |

O acervo saiu de 8.916 cartas publicadas para **10.824 cartas vivas** (publicadas
mais em fila de curadoria).

```
                                    antes      depois
cartas vivas ...................    9.384      10.824
sessões destiladas .............    7.412       9.196
grupos de texto idêntico .......        1           1     ← a trava segurou
```

**A dedup passou no teste que importa:** 1.780 conversas novas entraram e o número
de duplicatas exatas **não mudou**. As três travas — sessão, lote e `card_hash` —
funcionaram sem exceção.

---

## 2. Como o trabalho foi organizado

O desenho não é meu, é o de 29/07: **o modelo pensa, o script carrega.**

```
exportar.py    banco → disco, já mascarado, sem passar pelo contexto de ninguém
subagente      lê o pacote, escreve o destilado. Só faz o que só ele sabe fazer
validar.py     reprova antes de qualquer coisa tocar o banco          ← NOVO
aplicar.py     grava pelas regras de _store_card_sync
curadoria      junta as quase-cópias (limiar 0,47 medido), publica no RAG
```

### 2.1 O validador, e a prova de que ele consegue reprovar

`aplicar.py` grava o que recebe. Um `id` trocado grava conhecimento na conversa
errada; um arquivo com 68 linhas em vez de 70 perde duas conversas **em silêncio**,
e elas voltam à fila para sempre porque `distilled` nunca é escrito.

Antes de confiar no validador, provei que ele falha (§9.2):

```
CONTROLE  saída real e correta ................ passou    ✅
defeito   CPF plantado num fato ............... reprovou  ✅
defeito   uma conversa sem saída .............. reprovou  ✅
defeito   tipo fora do vocabulário ............ reprovou  ✅
defeito   score 999 .......................... reprovou  ✅
```

A linha de controle é o que dá direito à conclusão. Sem ela, um validador que
aprovasse tudo pareceria idêntico a um que funciona.

---

## 3. Os quatro achados convergentes

Vinte e sete destiladores leram pacotes diferentes sem se falarem. Quatro coisas
apareceram em quase todos os relatórios. **Convergência independente vale mais que
qualquer observação isolada.**

### 3.1 📊 O áudio é o maior sumidouro do acervo — e o padrão assusta

Relatado por 15 dos 27 pacotes. Entre 12 e 20 conversas de cada 70 têm a resposta
decisiva em `[audio]`, com só o *"ok, entendi"* chegando ao texto.

E o padrão que um destilador formulou melhor que os outros:

> **"Quanto mais resolutivo o atendimento, mais ele acontece em áudio."**

A pergunta do segurado fica escrita. A explicação da atendente — que é a carta —
vira `[audio]`. O acervo guarda sistematicamente a dúvida e perde a resposta.

Casos concretos citados: *"troca de vidro precisa de BO?"* apareceu duas vezes e
foi respondida por áudio nas duas. Uma pergunta perfeita sobre assistência
residencial dentro de assistência auto ficou sem resposta no transcript.

**Consequência para o plano:** repartear a AutoFleet para salvar os 1.623 áudios
provavelmente rende mais cartas que destilar todo o resto do texto. A pendência
que foi adiada é hoje a de maior retorno medido.

### 3.2 📊 O rótulo `CLIENTE` quase nunca é o segurado

Entre 20 e 58 conversas de cada 70. Quem está do outro lado é o robô da URA, a
central da Autoglass/Maxpar/Pilkington/Carglass/Localiza, a corretora parceira, a
analista da seguradora, a oficina, ou o colega da própria equipe.

Isto **não** é a regra de papéis trocados (mensagem encaminhada). É outra coisa, e
a consequência é melhor do que parece:

| campo | o que fazer | por quê |
|---|---|---|
| `fatos_reutilizaveis` | preencher, e generosamente | a mensagem automática **enuncia a regra literal e completa** |
| `resumo_conduta` | vazio | ensinaria a conduzir como se fala com um colega |
| `perguntas_na_ordem` | vazio | as perguntas são do robô |
| `score` | **0**, não nota baixa | não houve atendimento humano a avaliar |

Virou a **regra 8** do prompt no meio da rodada. Um destilador resumiu: *"melhor
fonte de fato, pior fonte de conduta."* Vários relataram que as conversas de robô
produziram os melhores fatos do pacote inteiro.

### 3.3 📊 Zero conversas de cobrança pós-boleto em 1.784 lidas

Todos os pacotes relataram, sem exceção. Nenhum boleto, nenhuma parcela em aberto,
nenhuma reprogramação, nenhuma pergunta de vencimento.

**Isto é achado duro para o Auxiliar de Cobrança:** o material dele **não está
neste canal**. O briefing pedia especificamente "a conversa depois do boleto" como
o ouro escasso — e ela não existe aqui. Ou acontece por outro número, ou por
telefone, ou não acontece.

Um destilador achou a exceção que confirma a regra, e ela é valiosa: **apólice com
prêmio pendente trava o sinistro.** A Tokio Marine não envia nem a relação de
documentos do terceiro enquanto houver parcela em aberto. É uma amarra entre
cobrança e sinistro que nenhum dos dois trabalhadores acharia sozinho — e estava
escondida numa conversa interna.

### 3.4 Conhecimento que só serve para burlar — e a recusa

Cinco pacotes encontraram conversas em que a equipe combina:

- emitir ou incluir o veículo **depois** do evento
- registrar data de ocorrência diferente da real
- omitir o boletim porque *"essa seguradora não tá muito exigente ultimamente"*
- pedir carro reserva como pane quando o evento foi roda/pneu, sem contar ao segurado
- reescrever relato de vandalismo como colisão para caber na cobertura
- responder ao segurado que ele "pode informar qualquer data" que não lembra

Os destiladores **recusaram** escrever qualquer uma como carta. E um explicou o
perigo com precisão:

> *"O material sai bem-formado e passaria em qualquer teste de qualidade formal."*

*"A seguradora X tem exigido menos documentação em sinistro de pequeno valor"* é
verdadeira, verificável e está no nível certo de generalidade. Ela só falha no
único teste que importa: **para que serve?**

Virou a **regra 11**: *"se o agente de atendimento usar esta carta na frente de um
segurado, o que acontece? Se a resposta for 'a corretora comete fraude', não é
carta."*

🧑 **Isto é observação sobre conduta interna registrada em conversas de julho, não
sobre o sistema.** Não cabe a mim decidir o que fazer com essa informação — está
registrada aqui porque esconder seria pior.

---

## 4. O número que mentia

📊 Depois da rodada, o sistema reporta **1.779 sessões pendentes de destilação**.

Medido: **1.775 delas têm menos de 80 caracteres.** São *"ok"*, *"obrigada"*,
recado, confirmação. O exportador as pula por regra, e o destilador automático
também — elas **nunca** virarão carta e **nunca** sairão da fila.

Destiláveis de verdade: **4**. Todas processadas.

Isto é o §12.1 na prática: o campo diz "pendente" e guarda "impossível". Registrado
aqui em vez de corrigido, porque marcar 1.775 linhas é escrita em massa e merece
decisão explícita — mas o número não deve ser lido como trabalho a fazer.

---

## 5. As regras que nasceram durante a rodada

O prompt começou com 7 regras e terminou com 11. As quatro novas vieram do que os
destiladores acharam, não do que eu previ (§9.3 — a lição migra):

| # | regra | de onde veio |
|---|---|---|
| 8 | interlocutor trocado ≠ papéis trocados | 5 destiladores relataram sem combinar |
| 9 | score 0 ≠ score baixo | "nota baixa em conversa sem atendimento estraga a régua" |
| 10 | nome que parece seguradora e não é | "Exclusiva", "Alpha" são empresas seguradas |
| 11 | conhecimento que só serve para burlar não vira carta | 5 pacotes, recusa correta |

---

## 6. O que ficou de fora, e por quê

- **Áudio** — 1.623 arquivos da AutoFleet só se salvam com repareamento. 🧑 Founder.
- **Curadoria fina por seguradora** — 📊 7.472 das 10.824 cartas estão sem
  seguradora, e isso está **certo** (regra 3: só quando escrita). Mas várias delas
  são regras que outra seguradora poderia fazer diferente. Cruzar o `id` da conversa
  com a apólice no banco multiplicaria o valor dessas cartas. Não foi feito.
- **A categoria "o que o documento não pode dizer"** — um destilador achou um
  orçamento de oficina que descrevia agravamento de risco escrito pela própria
  oficina, dentro de um documento que a corretora ia anexar. Não é "prazo" nem
  "documento exigido". Sugerido como categoria nova; não criada.
- **Marcar as 1.775 curtas** — decisão do Founder.

---

## 7. Declaração

Nenhum motor paralelo foi criado. Toda a rodada usou `exportar.py`, `mascarar.py`,
`aplicar.py` e `curadoria_cartas.py` existentes. O único arquivo novo é
`validar.py`, que é portão e não motor — ele não grava, só reprova.

Nenhum segredo aparece neste documento. Nenhum dado pessoal atravessou para as
cartas: três camadas de PII (máscara na exportação, instrução ao modelo,
reconferência na publicação) mais o validador novo como quarta.
