---
> **Status:** relatório final de execução — pré-condição do gate
> **Criado em:** 23/08/2026
---

# Relatório de execução — SPEC-084.2: O CONTRATO

**Produto:** AutoBrokers Intelligence OS
**Branch:** `feat/spec084-a-fabrica-de-rotas` · **Worktree:** `AutoBrokers-FIX`
**Executor:** Claude Opus 5 (1M), com 5 subagentes de investigação e 5 juízes
**Início e conclusão:** 23/08/2026
**Commit inicial:** `0d98b19` · **Commit final:** ver §12
**Estado final:** CONCLUÍDA COM RESSALVAS — *a liberação é do juiz*

> **O achado, na frase que o define:**
> *As 19 rotas AAA respondiam 100% das telas da URA, com 100% de determinismo.
> E nenhuma passava o portão da ferramenta.*

> 🔴 **Correção de linguagem, exigida pelo JUIZ 4 e adotada:** onde este
> relatório dizia *"as 19 rotas acionam"*, leia-se **"passam o PORTÃO"**.
> `acionar` é o que acontece na seguradora, e **nenhum acionamento real foi
> feito nesta SPEC** — as proibições do Founder o impedem. Ver §3.6.

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado. O corredor continua **um só**, a régua
      **uma só**, o motor **um só**. O `friendly` da ferramenta — que era uma
      segunda fonte de verdade — foi **removido**, não substituído.
- [x] Nenhuma migration foi criada, movida ou aplicada. **Esta SPEC não tocou
      em SQL.**
- [x] Nenhum segredo exposto. Auditoria de PII rodada; ver §7.
- [x] Nenhum escopo reduzido. Os seis consertos foram executados.
- [x] As seis proibições cumpridas: ✗ não ligou agente · ✗ não enviou mensagem
      · ✗ só `SELECT` · ✗ não acessou portal · ✗ não imprimiu segredo · ✗ não
      fez merge na `main`.

---

## 1. O achado, e o controle que o define

📊 Rodado no motor real, pelo caminho que o LLM percorre — só os campos que
`InsurerDispatchInput` **declara** podem chegar a `build_dry_run_plan`:

```
com TUDO que a ferramenta consegue carregar   →  missing_data     0 de 19
com os slots que ela NÃO carrega, em memória  →  ready_to_send   19 de 19
```

🔴 **O corredor estava certo. O bloqueio estava ANTES dele** — no contrato, que
é onde a régua da SPEC-084.1 não olha. E a causa foi a própria SPEC-084.1: ela
acrescentou slots a `required_slots` e não estendeu o schema.

⚠️ A prova de que a pergunta era legítima já estava escrita: 📊 **19 dos 22
slots já tinham redação em `_COMO_PERGUNTAR`.** O produto sabia perguntar e não
sabia guardar.

---

## 2. Os seis consertos

### C1 · O contrato não tinha campo para o que o portão exige

**Decisão, por nota:** (a) acrescentar campos **72** · (b) portão consultar o
padrão do motor e o galho condicional **58** · **(c) as duas, cada uma no seu
caso — 94** ✅

📊 Medi a origem dos 16 slots órfãos. **Nenhum tem constante no subserviço** —
nenhum é "o motor preenche". Mas se dividem em duas causas **opostas**:

| | quantos | por quê |
|---|---|---|
| **pergunta de verdade** → (a) | 14 | `local_seguro` sozinho bloqueia 13 rotas, e o corredor diz por que não tem default: *"responder 'sim' no escuro **rebaixa a prioridade** de quem está parado num lugar perigoso"*. `idade_aparelho_opcao` decide COBERTURA |
| **filho de galho não tomado** → (b) | 2 | `transporte_destino` e `taxi_passageiros` pendem de `meio_de_transporte`, cujo default é `"Não"` — o produto exigia saber *"para quantos passageiros no táxi?"* de quem pediu guincho |

🔴 Um remédio só erra numa das duas, e o erro de (b) aplicado aos 14 é o pior
possível: **um portão que libera acionamento sem saber se a pessoa está segura.**

O mecanismo de (b) não é exceção nova: o portão já pula `fallback_adaptive` e
`noop`. **`sem_chute` é o terceiro membro da família** — o passo que declara
*"não tenho default honesto e escalo quando a tela aparecer"*. E não afrouxa:
📊 `taxi_passageiros` continua cobrado em `porto/auto/taxi`, a rota que É sobre
táxi.

🔴 **O guarda que o próprio C1 prometia e eu não tinha escrito** —
`test_o_contrato_alcanca_o_portao` — foi apontado por um subagente. Ele acusou
na estreia o que esta mesma edição deixara passar: **16 slots órfãos em rotas
fora das 19**. Fechar só o que o gate mede é comprar o gate.

✅ **E a P-084-61 fechou**, porque a razão de estar travada deixou de existir:
`zurich/auto/guincho` exigia `local_seguro` **e** `local_seguro_opcao` — o mesmo
fato com dois nomes, duas perguntas ao segurado.

### C2 · O formulário nativo travava na PENÚLTIMA tela

```
montar_resposta_de_flow(flow, caso COMPLETO)  →  ok=False
   missing = rb_EmGaragemOuEstacionamento, rb_NivelDaRua, rb_InformacoesLocal
CONTROLE, mesma sessão + os três slots       →  ok=True
CONTROLE NEGATIVO, tirando UM por vez        →  cada slot derruba UM campo
```

🔴 O desfecho era o pior possível: a sessão nascia `ready_to_send` — o produto
**prometia** acionar —, falava ~25 telas com a URA e morria na penúltima, com o
segurado esperando na rua.

⚠️ E o C2 causou uma perda que eu não tinha visto: com os três em
`required_slots`, a lista de coleta passou a montá-los pela origem `subservico`
e eles **perderam a pergunta e as opções exatas da seguradora**. `_somar` agora
ENRIQUECE em vez de ignorar.

### C3 · A ferramenta dizia "a hdi não atende socorro mecânico" — sobre uma rota AAA

**Decisão, por nota:** (A) manter a lista à mão, completando-a **12** ·
**(B) DERIVAR dos playbooks — 94** ✅

📊 A lista literal de cinco nomes não conhecia os quatro subserviços de auto que
nasceram depois dela, conhecia `pane_seca` (que é apelido, não rota), e comparava
a string **crua**.

🔴 A prova que decidiu: **derivada dos 14 playbooks, a tabela aponta UM ÚNICO
subserviço ambíguo — `chaveiro` — que é exatamente a exceção que a lista à mão
precisava declarar num SEGUNDO lugar.** Uma derivação que descobre sozinha a
única exceção que a lista tinha de escrever prova que a lista era um resumo mal
copiado da tabela.

```
rotas com corredor errado    5 → 0
rotas em handoff (chaveiro) 14 → 14      ← o guarda NÃO afrouxou
apelidos de auto que erram  25 → 0
```

⚠️ E `chave`, apelido de `chaveiro`, **contornava o guarda do chaveiro**: o ramo
do handoff também comparava a string crua. O incidente que o comentário dizia
impedir acontecia por baixo dele.

### C4 · A yelum tem QUATRO formulários; o produto conhecia UM

📊 Varredura própria dos 28.096 eventos:

```
857030507196739   (veículo, local e ocupantes) V2   hdi   18/07   ✅ registrado
2887131368288279  (local e ocupantes)               yelum 07/08 e 17/08
3206000179602236  (veículo, local e ocupantes) V2   yelum 19/08
1579547063352571  Informar endereço V2              yelum 03/08   ⏸️ P-084-68
```

**Decisão:** (A) reusar o V2 inteiro **12** · **(B) registro próprio reusando as
TELAS por referência — 94** ✅. (A) foi medida e reprovada: reusar o V2 exigiria
dois campos que este formulário **não mostra** — `formulario_incompleto` em 100%
dos casos, para sempre.

🔴 **E o registro revelou três rotas que ninguém via:** `hdi/auto/chaveiro`,
`yelum/auto/pneu` e `yelum/auto/socorro_mecanico` — esta última uma rota 88/88 —
batiam no formulário e não o respondiam. **É a medição que muda o escopo, não a
preferência.**

### C5 · Três textos chegavam errados ao cliente — e o defeito era de classe

| defeito | o que o cliente lia |
|---|---|
| marcador interno | *"📊 A senha da visita técnica…"* — 📊 significa "número medido" |
| instrução de outro serviço | socorro mecânico: *"alguém para acompanhar o **guincho**"* |
| identificador cru | dossiê ao humano: *"Motivo: sem_chute:transporte_destino"* |

📊 **A classe varrida:** 9 pares herdavam o texto do guincho sendo outra coisa.
Os que têm texto medido ganharam o próprio; os que não têm tela de orientação
ganharam **silêncio** — e para o silêncio existir, `[]` precisou vencer o `or`.

🔴 **Duas afirmações caíram por não estarem no corpus:** *"sem a senha o
prestador não executa o serviço"* e *"a mão de obra é que está coberta"* —
verdade no encanador, **falsa** no eletrodoméstico, onde a mesma URA diz
*"coberto a mão de obra E PEÇAS"*. Regra de CORREDOR não decide cobertura de
ROTA.

⚠️ **Dois defeitos latentes que o texto novo expôs:** o limiar do deduplicador
era proporcional ao texto NOVO (quanto mais rica a redação, mais impossível
colapsar), e **a pontuação entrava na assinatura** — `local` e `local.` eram
palavras diferentes, e a interseção encolhia a cada ponto final.

### C6 · A régua PREMIANDO o buraco

**Decisão, por nota:** (a) sempre RESPONDIDA quando monta **35** · (b) sempre
ORFA_FUNCIONAL **55** · (c) classe nova **25** · **(d) as duas conforme o
produto consiga montar — 92** ✅

📊 `replay.py` nunca chamava `detect_native_flow`; `regua_motor` nem a
reexportava. A tela que TRAVA o acionamento saía do denominador como
`ORFA_INOCUA`, e *"zero órfãs funcionais"* dava 20/20 a duas rotas.

🔴 **Este furo não é o do C8.** O C8 era a régua punindo o comportamento certo.
Este é o inverso, e o mais perigoso: **a régua premiando o buraco.**

⚠️ E o formulário é consultado **ANTES** do passo — única divergência declarada
em relação ao motor. Sem isso, três linhas de âncora de texto comprariam os 20
pontos de volta. 📊 Custo da inversão hoje: **zero**.

---

## 3. O par C6 → C2 → C4, e por que ele é a prova

| momento | hdi/guincho | yelum/guincho | AAA | média |
|---|---|---|---|---|
| antes da 084.2 | 102/106 | 102/106 | 19 | 88,4% |
| **depois do C6** | **82/106** | **86/106** | **17** | **87,6%** |
| depois do C2 | 102/106 | 102/106 | 19 | 88,4% |
| **depois do C4** (só o registro) | 102 | 102 | **17** | **87,5%** |
| **final** | 102/106 | 102/106 | **19** | **88,4%** |

🔴 **A volta é a prova.** O mesmo número, antes pago por uma tela escondida,
agora é ganho por uma tela respondida. As cinco rotas com formulário têm hoje
`of=0` e **todas as telas RESPONDIDA**.

---

## 3.1 A rodada dos juízes — e ela mudou a SPEC

Cinco juízes, e **dois reprovaram**. O laço é da SPEC: *"a liberação é do juiz"*.

| juiz | nota | veredito | o que achou |
|---|---|---|---|
| 0 · a régua | **86** | APROVADO | 🔴 um **fail-open** meu: o contador de mutações devolvia 6 pontos quando não conseguia ler o arquivo |
| 1 · a cobertura | **68** | 🔴 REPROVADO | dois BLOCKERs: quem paga a peça, e uma cobertura inventada |
| 2 · a segurança | **78** | APROVADO | 🔴 P1: o **endereço** respondia a pergunta de segurança |
| 3 · o segurado | **82** | APROVADO | a linha que diz *quando* alguém chega era cortada por um `[:2]` |
| 4 · o contrato | **62** | 🔴 reprova a **afirmação** | *"19 de 19 acionam"* media a ENTRADA do corredor |

### O que cada um achou, e o que era meu

🔴 **JUIZ 2 (P1) — o pior de todos, e era meu.** O C2 copiava
`situacao_risco_opcao` para `local_situacao`, e aquele slot era derivado varrendo
`local_atual` — o **endereço**. 📊 Medido: um carro no km 42 de rodovia, com
*"em frente ao posto de gasolina"* no endereço, fazia o produto enviar
`rb_InformacoesLocal="6"` = **LOCAL SEGURO** à seguradora. O comentário que eu
mesmo escrevi no C2 diz que isso *"rebaixa, no escuro, quem está parado num
lugar perigoso"*.

⚠️ E a primeira redação do conserto foi **grossa demais**: proibir o ramo seguro
de ler `local_atual` reprovava *"estou no estacionamento do shopping, bem
iluminado"*, que é o segurado dizendo onde está. **O que envenena não é o campo,
é a FORMA:** *"em frente ao posto"* descreve o que se VÊ; *"dentro do posto"*,
onde se ESTÁ.

🔴 **JUIZ 1 (BLOCKER) — o C5 consertou metade do defeito que ele mesmo nomeou.**
Tirou o parêntese *"(a mão de obra é que está coberta)"* e **deixou a oração
principal** — que é a que decide quem paga. 📊 A URA da yelum diz *"material por
conta do segurado"* só em encanador e eletricista; em eletrodomésticos ela diz
**"coberto a mão de obra E PEÇAS"**. O produto dizia ao segurado da geladeira
que a peça é por conta dele.

🔴 **JUIZ 4 — a afirmação central estava errada.** *"19 de 19 acionam pelo
caminho real"* mede a ENTRADA do corredor. Rodando as telas REAIS do corpus pelo
motor, rotas AAA iam a `needs_human` por slots `_opcao` que um PASSO exige, o
motor não injeta, e a regra do sufixo isentava. **As duas regras se
contradiziam:** uma diz *"o motor preenche"*, `sem_chute` diz *"não existe
default honesto"*.

**A distinção que faltava ao C1: CARREGAR não é COBRAR.**

```
o PORTÃO não cobra  →  ninguém é interrogado à toa por um galho que quase
                       nunca é tomado
o CONTRATO carrega  →  quando o galho É tomado, a resposta tem onde morar
```

Eu tratei as duas como a mesma decisão. São opostas.

🔴 **E o guarda que escrevi era CIRCULAR:** sua população eram os
`missing_slots` do portão — exatamente o conjunto que esta SPEC estreitou. Ele
ficava verde enquanto rotas travavam.

🔴 **JUIZ 0 — um fail-open meu.** `_mutacoes_declaradas_no_repo` devolvia 0
quando não conseguia ler o arquivo, e o `and` curto-circuitava: o item de 6
pontos passava a valer 6 **em todas as rotas** com um número inventado. **Zero
MEDIDO e zero NÃO MEDIDO não são a mesma coisa.**

### E o portão passou a conferir VALOR, não só presença

📊 Um `local_situacao` com o texto *"na rua, em frente ao numero 100"* **passava**
o portão e morria na tela do formulário, depois de ~25 telas de URA, com o
segurado esperando. Agora o portão confere — só em campo de escolha fechada, e
pela **mesma função que o envio usa**, senão seriam duas verdades sobre o mesmo
valor.

### O que sobrou, e é limite declarado

📊 Quatro rotas ainda param no caminho inteiro, em
`formulario_pronto_sem_flow_token`: **o corredor MONTA a resposta e o canal não a
leva** — é a P-084-67, o `galaxy_message` que o parser não reconhece, medido em
**0 de 28.096 eventos**. Corredor e canal são coisas diferentes, e os guardas
passaram a distingui-las.

### 3.2 A SEGUNDA volta — e a nota caiu, porque eu piorei uma coisa

📊 O JUIZ 1 reprovou de novo: **68 → 61**. A queda é justa, e o motivo é o mais
instrutivo desta SPEC.

🔴 **Consertar o achado do JUIZ 3 criou um defeito maior.** Subir
`instrucoes[:2]` para `[:4]` fez a linha *"Você vai receber um SMS/link com a
previsão de chegada do prestador"* sair de **zero para dez rotas** de entrega ao
segurado — e ela não tem lastro:

```
telas com `sms` ou `previsão de chegada`, por corredor de auto:
   azul 0/321 · mapfre 0/75 · porto 0/521 · tokio 0/70 · yelum 0/607
```

Cinco corredores com **ZERO**. E onde existe, diz outra coisa: hdi e yelum
escrevem *"enviaremos **POR AQUI** o resumo e o link"* — o canal oposto. E a
previsão de chegada não está em SMS nenhum: 📊 as 23 ocorrências de *"previsão"*
no corpus estão dentro do próprio chat, na tela de resumo, **antes** de
confirmar.

⚠️ **E a condenação estava escrita por mim, no commit anterior**, na P-084-70:
*"afirmar sem base pode fazer o segurado adiar o atendimento"*. Descrevi a
classe, declarei a pendência, e no commit seguinte promovi mais um caso dela de
0 para 10 rotas.

A frase virou o que o produto **de fato faz**: *"assim que a seguradora me
passar a previsão de chegada, eu te aviso por aqui"* — verdade em todas as
rotas, e o canal certo justamente onde a URA diz *"por aqui"*.

### 3.3 🔴 E dois consertos meus tinham sido REVERTIDOS em silêncio

📊 Dois consertos já aplicados e verificados **sumiram do arquivo sem que
ninguém os desfizesse**. A causa é a mecânica da própria bateria:
`verificar_mutacoes` **copia** o arquivo, muta, roda e **restaura da cópia** — e
os juízes rodavam a bateria na MESMA árvore em que eu escrevia. Um deles copiou
antes de uma edição e restaurou depois.

⚠️ É a família da P-084-74, um nível pior: ali o guarda acusava **depois**; aqui
**não há guarda nenhum**, porque o arquivo restaurado é válido e todos os testes
passam — eles só medem uma verdade antiga.

🔴 **E o que revelou foi um juiz reprovando DUAS VEZES o mesmo defeito.** A
segunda reprovação não era teimosia dele: era o arquivo tendo voltado.

📊 **E o modo de conferir virou lição:** `grep` acusou o P1 de segurança como
revertido quando ele estava vivo — o padrão tinha acento diferente.
**Conserto se confere MEDINDO no motor, não procurando string.**

Está em [P-084-80], com o que destrava: juiz e executor não podem trabalhar na
mesma árvore.

### 3.4 Regra de cobertura passou a ter dono

*"A mão de obra é coberta; as PEÇAS são por conta do cliente"* é regra da
**Allianz** — e o briefing a lia à atendente que estava acionando a **Yelum**,
cuja URA diz o contrário em eletrodomésticos. 🔴 **O produto se contradizia
dentro do mesmo atendimento:** a atendente afirmava uma coisa e, vinte minutos
depois, o WhatsApp dizia a outra.

⚠️ Consertei primeiro no lugar errado — reescrevendo o texto de UMA regra — e
desfiz. O defeito não é da frase: é do **briefing**, que funde as seguradoras.
Agora cada bloco sai com `[SEGURADORA · serviço]`.

📊 Isso levou o bloco de 6.8k para 7.4k, acima do teto. **A saída não foi subir
o teto:** donos com regra idêntica dividem um bloco, e o cabeçalho encolheu →
**6.982 de 7.000**.

### 3.5 E o guarda que o juiz pediu duas vezes

> *"Nenhum guarda compara uma afirmação de cobertura contra o corpus da rota que
> a recebe. Enquanto isso não existir, esta auditoria só acontece quando um juiz
> a faz à mão."*

`test_a_cobertura_tem_lastro_no_acervo` — toda afirmação de cobertura que
alcança um humano tem de apontar uma tela do corredor que a recebe. Com os dois
lados do controle: a frase do SMS **é reconhecida** como afirmação e a porto tem
**zero** telas de `sms` (logo seria reprovada); a afirmação **verdadeira** sobre
classe de bônus **tem** tela.

### 3.6 🔴 O JUIZ 4 reprovou a AFIRMAÇÃO — duas vezes — e ele estava certo

📊 *"19 de 19 acionam pelo caminho real"* mede a **entrada** do corredor e era
apresentada como o corredor inteiro. E o achado que mais dói é sobre o método:

```
df89432  só os slots que o portão COBRA + relato realista →  34 capturas
0fbfcd8  só os slots que o portão COBRA + relato realista →  34 capturas
0fbfcd8  o caso cheio do medidor                          →  +9, e o "antes" só
                                                             tinha 11 sem_chute
                                                             porque o relato do
                                                             medidor era genérico
```

🔴 **As +9 capturas eram do INSTRUMENTO.** No mesmo commit em que declarei os
sete campos, eu os acrescentei ao `_PREENCHIMENTO` do medidor — e as derivações
que produzem aqueles valores já existiam antes. **O medidor mediu a própria
generosidade.**

⚠️ É a §9.2 virada contra mim: *"toda bateria precisa de controle"*. Eu rodei o
controle do PORTÃO (tirar o CPF) e não rodei o do INSTRUMENTO (medir com o que
o portão de fato cobra). O juiz rodou.

**O que a segunda volta dele consertou de verdade**, e ele confirmou por
medição: o portão confere valor pela mesma função do envio · `veiculo_nivel_rua`
ensina os quatro títulos e **os quatro resolvem** · a população do guarda deixou
de ser circular · o formulário passa a MONTAR · **zero regressões** (73/73 no
portão, nenhuma sessão perdeu captura) · o interrogatório é **idêntico** ao de
antes (565 slots cobrados nos dois commits).

**E os cinco itens que ele deixou nomeados foram executados:**

| item | o que era | estado |
|---|---|---|
| a frase do ar-condicionado | mandava usar `eletrodomesticos`, e o modelo apertava **1+15** numa URA cuja tela tem **2 = Ar Condicionado** | ✅ |
| valor recusado sem saída | mesma mensagem de "dado ausente" → o atendente reenviava o mesmo valor → **laço fechado** | ✅ agora lista os títulos aceitos |
| conferidor sem escopo | um valor ruim bloqueava **10 rotas**, e 8 nunca abrem aquele formulário | ✅ **10 → 2** |
| `bateria_tipo_opcao` | *"galho raro"* — 📊 e é tomado em **7 de 7** sessões de bateria | ✅ passa a ser cobrado |
| controle da metade nova do guarda | apagar a varredura dos `requires` não derrubava nada | ✅ |

---

## 4. Migrations

**N/A — justificado.** Nenhuma migration criada, alterada ou aplicada. A
proibição nº 3 do Founder (*"PROIBIDO ESCREVER NO BANCO"*) tornaria qualquer
migration uma violação; as leituras foram exclusivamente `SELECT`.

---

## 5. Testes — com saída real

```
$ python scripts/verificar_mutacoes.py
  -> 12 de 12 mutacoes EXECUTADAS e vermelhas

$ python scripts/acionamento_pelo_contrato.py
  ACIONAM: 19 de 19                                    (era 0 de 19)
  CONTROLE 2: 19 de 19 continuam bloqueadas sem o CPF
  CONTROLE 3: cada campo novo derruba as rotas que o exigem
```

**Guardas novos desta SPEC:**

```
test_o_contrato_alcanca_o_portao.py            6 asserções
test_a_linha_do_servico_vem_do_corredor.py    21 asserções
test_o_formulario_nao_e_inocuo.py             27 asserções
test_o_cliente_nao_le_marcador_interno.py     16 asserções
```

**Guardas existentes atualizados (§9.3 — a lição migra, não morre):** cinco.
Cada um afirmava o defeito como invariante e passou a afirmar o conserto, com o
motivo e a data em que a condição mudou.

---

## 6. O que continua vermelho, e a prova de que é anterior

`test_golden_do_eletricista`, `test_handoff_chega_em_alguem`,
`test_corredor_residencial_yelum`, `test_o_acionamento_nao_pede_o_impossivel`,
`test_spec017_dispatch` e outros — **provados vermelhos no commit anterior**,
num `git worktree` em `HEAD`, **com linha de controle**: um teste sabidamente
verde rodou verde lá.

⚠️ Sem esse controle a medição mente: 📊 na primeira tentativa o worktree nem
chegou a ser criado (`Filename too long`), e **todas** as linhas saíram *"já
estava vermelho"* — porque o `cd` falhava e o `||` disparava.

---

## 7. Segurança e PII

- 📊 `scripts/auditar_pii_no_codigo.py` rodado no escopo desta SPEC.
- ⚠️ **O repositório era público e o Founder o tornou privado durante a
  execução.** A limpeza dos ~89 identificadores restantes segue em
  `CHANGE-ADDENDA` como ESSENCIAL, aguardando autorização (P-084-66).
- Nenhum dado de pessoa foi introduzido por esta SPEC.

---

## 8. Riscos remanescentes

| # | risco | gravidade | onde está |
|---|---|---|---|
| 1 | 🔴 **o `flow_id` nunca chega** — sem isso, C2 e C4 entregam dossiê, não acionamento automático | alta | P-084-67 |
| 2 | a mutação foi commitada **pela segunda vez**; o guarda só acusa depois | alta | P-084-74 |
| 3 | o 4º formulário da yelum não foi transcrito, e um passo responde texto a ele | média | P-084-68 |
| 4 | qual `flow_id` ecoar à yelum não é decidível offline | média | P-084-69 |
| 5 | a regra dos "18 anos" é afirmada em 6 corredores onde o acervo não a mostra | média | P-084-70 |
| 6 | `confirm_first` roda antes da validação de subserviço | média | P-084-77 |

---

## 9. Canário Amandus → Resulta → AutoFleet

⚠️ **NÃO EXECUTADO — é proibição do Founder, não omissão.** O canário exige
ligar agente e enviar mensagem, as duas primeiras proibições.

| | prova | não prova |
|---|---|---|
| o gate do contrato | que o dado TEM COMO chegar ao portão | que a URA aceita a resposta hoje |
| replay contra 43 corpora | que o corredor responde a tela real | que a mensagem SAI pelo canal |
| 12 mutações | que os guardas veem o que dizem ver | que o `flow_token` chega (P-084-67) |

---

## 10. Declaração final

**FATO.** Seis consertos executados, medidos e commitados sozinhos.
📊 **As 19 rotas AAA passam o PORTÃO da ferramenta com o caso cheio — eram 0 de
19.** Rodando as telas gravadas do corpus pelo motor, **16 dessas 19 chegam a um
protocolo em ao menos uma sessão**, e **34 das 72 sessões** chegam; das 38 que
não chegam, **25 param por motivo legítimo** (17 `handoff_trigger`, 8
`insurer_closed`), **8 têm a gravação interrompida** e **5 param em
`formulario_pronto_sem_flow_token`** — resposta montada, sem canal (P-084-67).

⚠️ 📊 **E o ganho de capturas foi do MEDIDOR, não do produto.** Com apenas os
slots que o portão COBRA e um relato realista, o número de capturas é **o mesmo
de antes da SPEC**. Os sete campos novos são um SEGUNDO caminho para dados que
a derivação por relato já produzia — robustez plausível, **não medida**. 💭
Nenhum acionamento real foi feito. O portão continua
cobrando o que é legítimo (controle 2 e 3). 12 de 12 mutações vermelhas. A régua
passou a enxergar o formulário nativo, e a nota caiu e voltou, agora ganha.
Nenhum motor paralelo foi criado.

**INFERÊNCIA.** As 19 rotas *devem* levar um acionamento do começo ao fim — mas
isso é inferido de replay contra corpus gravado e de simulação do portão, **não
de um acionamento real**. E há um limite medido: enquanto o `flow_token` não
chegar (P-084-67), as rotas com formulário pausam com a resposta pronta em vez
de enviá-la.

**RECOMENDAÇÃO.** Ligar a leitura de `galaxy_message` (P-084-67) é o próximo
bloco, e é o que separa "dossiê pronto" de "acionamento automático". Depois,
o canário na Amandus.

> 🔴 **A LIBERAÇÃO É DO JUIZ.** Este relatório é a pré-condição do gate, não o
> gate. Nenhum merge na `main` foi feito.
