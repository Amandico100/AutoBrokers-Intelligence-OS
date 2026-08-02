# O que a pesquisa de 30/07 descobriu — em português de negócio

> Este arquivo existe porque o primeiro relatório foi escrito em linguagem de
> analista e não ficou claro. Aqui está a mesma coisa, começando pelo dinheiro.

---

## A ideia em uma frase

**Descobrimos que dá para o AutoBrokers dizer ao corretor coisas que hoje
ninguém no Brasil diz a ele — e cada uma dessas coisas muda uma decisão que
vale dinheiro.**

Não é "informação de mercado". É munição para ele ganhar mais, gastar menos e
não perder cliente.

---

## As cinco coisas que descobrimos, e o que cada uma vale

### 1. Dá para saber qual seguradora paga bem e qual enrola

A SUSEP publica, de graça, **quanto cada seguradora recebeu de prêmio e quanto
pagou de sinistro**, por ramo, por estado, todo mês, desde 1995.

Ninguém usa esse dado porque ele vem num arquivo bruto de 542 MB e **a coluna
que a documentação manda usar está zerada desde 2013** — quem segue o manual
calcula 0% e não percebe. Nós descobrimos qual é a coluna certa.

> 💭 **Aviso acrescentado em 02/08/2026.** Todos os blocos *"O que isso vira na
> tela"* neste documento são **copy ilustrativa** — texto de exemplo, com números
> inventados para mostrar o formato. **Nenhum deles é medição.** Estavam
> formatados igual a dado real, e foi assim que um deles atravessou seis
> documentos como se fosse um achado. Ver CLAUDE.md §12.1.

**O que isso vira na tela do corretor:**

> *"Você está colocando 40% do seu auto na Allianz. A sinistralidade dela em
> auto-casco é **69,3%**. A da Porto é **57,7%**. Uma seguradora que paga mais
> sinistro do que arrecada aperta em três lugares: demora mais para liberar,
> nega mais, e é a primeira a cortar sua comissão na renovação. **Vale começar a
> equilibrar.**"*

**Vale quanto:** a comissão de auto fica entre 10% e 20%. Um ponto de comissão
numa carteira de 900 apólices de R$ 2.400 é **R$ 21.600 por ano**. E a
sinistralidade prevê o corte antes de ele acontecer.

---

### 2. Dá para saber a franquia e a cobertura reais da apólice DAQUELE cliente

**As Condições Gerais de todos os produtos de seguro do Brasil são públicas.**
Consulta por número de processo SUSEP, sem senha, sem CAPTCHA, e devolve o PDF.

E o mais importante: **devolve TODAS as versões, com data**. O produto de auto
da Allianz mudou **72 vezes**.

**Por que a data é tudo:** para responder *"esse sinistro tem cobertura?"*, vale
a versão que estava valendo **no dia em que a apólice foi assinada** — não a de
hoje. Quem indexar só a versão atual responde errado e não percebe.

**O que isso vira na tela:**

> *"O cliente tem apólice de fevereiro de 2024. **Naquela versão** das condições,
> vazamento por corrosão de tubulação embutida era excluído. A versão de 2026
> passou a cobrir. **Como a apólice é da versão antiga, esse sinistro será
> negado** — e o argumento para pedir reanálise está na cláusula 4.2."*

**Vale quanto:** hoje o corretor abre o PDF à mão, ou chuta. Isso é a diferença
entre prometer o que a apólice não cobre (e perder o cliente no pior momento) e
saber antes.

---

### 3. Dá para avisar que a comissão dele está presa — antes de sumir

**A seguradora só libera a comissão quando o cliente paga a parcela.** Se o
cliente atrasa, a comissão não é gerada. **O corretor descobre quando a apólice
já foi cancelada.**

Nosso robô da Allianz **já lê esse dado todo mês** — valor da comissão e data
prevista de cancelamento, parcela por parcela. E o sistema **joga fora** o campo
da comissão antes de gravar.

**O que isso vira na tela:**

> *"**R$ 2.180 da sua comissão não foi gerada** porque 41 parcelas estão
> atrasadas. **6 apólices têm cancelamento previsto para os próximos 15 dias** —
> são R$ 2.450 por ano de comissão recorrente que você perde se elas caírem. Já
> mandei o boleto para 35 clientes. Estes 6 não têm WhatsApp válido."*

**Vale quanto:** numa carteira de 900 apólices com 5% de inadimplência,
**R$ 1.500 a R$ 2.500 por mês** — dinheiro dele, que ele não sabia que estava
parado.

---

### 4. Dá para conferir a apólice antes de o erro virar prejuízo

Os dois casos abaixo são reais, de reclamação pública:

```
código FIPE errado na apólice ....... R$ 8.000 a menos na indenização
estado civil errado no cadastro ..... R$ 2.030 glosados
```

**Os dois erros foram cometidos na emissão e descobertos no sinistro** — meses
depois, quando não dá mais para consertar.

**O que isso vira na tela:**

> *"12 apólices emitidas esta semana. Duas com risco: a 3341 tem FIPE de Corolla
> **2020** (R$ 78.400), e o documento do cliente diz **2021** (R$ 86.800).
> **Diferença de R$ 8.400 na indenização.** Corrija por endosso agora — de
> graça."*

**Vale quanto:** ~2 erros materiais por mês numa corretora média. **É o
entregável mais indefensável de ignorar** — porque quando estoura, estoura na
cara do corretor.

---

### 5. Dá para tirar da seguradora a alavanca que ela usa no sinistro

**Quando a seguradora pede um documento a mais, o prazo de 30 dias para pagar é
SUSPENSO** e só volta a correr quando o documento chega.

**Não é desorganização. É um mecanismo que a regra permite** — e por isso "me
pediram o mesmo documento três vezes" é a reclamação mais comum do setor.

Nós temos **8.916 cartas de conhecimento destiladas de 8.800 atendimentos
reais** que sabem, por seguradora e por tipo de sinistro, o que vai ser pedido.

**O que isso vira na tela:**

> *"Sinistro de colisão, Porto, apólice 4471. **A lista COMPLETA que a Porto vai
> pedir — toda de uma vez, não em fatias:** [11 itens, cada um com o formato
> aceito]. Já mandei ao cliente. **Prazo: 30 dias, vence 29/08.** Se a Porto
> pedir documento novo depois desta lista, **o prazo não reinicia
> legitimamente** — me avise que eu registro a data."*

**Vale quanto:** semanas de ciclo, e a retenção do cliente no momento mais
emocional que existe.

---

## Quem é a "Segura", e por que ela importa

**Segura é uma empresa brasileira, fundada em março de 2025, que levantou
R$ 45 milhões em abril de 2026** com dois dos maiores fundos do mundo (a16z, que
investiu no Facebook e no Airbnb, e Kaszek, o maior da América Latina).

**O produto dela chama "Helena"** — um assistente de inteligência artificial que
funciona **dentro do WhatsApp do corretor**. Ele pergunta sobre a apólice do
cliente, sobre cotação, sobre renovação, e a Helena responde.

**É de graça para o corretor.** Zero reais.

Ela saiu de 100 corretores para **mais de 4.000 em quinze meses**, e a meta
declarada é 10.000 até o fim de 2026. O alvo dela são corretoras de até sete
funcionários — **exatamente o mesmo cliente que a gente quer.**

### Então ela é um concorrente. E é sério.

Sim. **É o concorrente mais bem financiado do nosso mercado, ele é gratuito, e
tem quinze meses de vantagem.**

### Mas ela tem um flanco, e ele é permanente

**A Segura não ganha dinheiro do corretor. Ela ganha das seguradoras** — recebe
uma porcentagem sobre o negócio que passa por ela.

Isso significa que **o cliente que paga a conta dela é a seguradora.**

E aí está o ponto:

> **Nenhum produto pago pelas seguradoras vai dizer a um corretor que a Allianz
> está com 69,3% de sinistralidade contra 57,7% da Porto.**
>
> **Nenhum vai dizer "a Porto te pagou R$ 1.847 a menos no extrato do mês
> passado".**
>
> **Nenhum vai dizer "essa seguradora demora o dobro para liberar".**

Não é que eles não pensaram nisso. **É que eles não podem.** Seria morder a mão
que paga.

**Tudo que é adversarial à seguradora está permanentemente fora do roadmap
deles** — e é justamente onde está o dinheiro do corretor.

### A frase de venda que sai disso

> *"Um sistema pago pelas seguradoras tem interesse em colocar seu negócio na
> seguradora que paga melhor **para ele**.*
> *Um sistema pago por você tem interesse em colocar na que atende melhor **o
> seu cliente**."*

### E a parte honesta

**Vamos perder o corretor que só quer um assistente de WhatsApp.** Contra
grátis, não há o que fazer — e esses nunca pagariam nem R$ 52/mês.

O nosso cliente é quem tem carteira grande o suficiente para o dinheiro achado
superar o preço: **a partir de ~700 apólices**. Para esse, R$ 400 a R$ 600 por
mês contra R$ 3.500 a R$ 5.000 encontrados é uma conta que **ele mesmo faz**.

---

## O que isso muda no sistema — em português

### A regra que organiza a ingestão de dados

Antes eu escrevi *"número vai para tabela, cláusula vai para RAG"*. Traduzindo:

**Número não pode virar texto.** Se eu guardar "a Porto arrecadou R$ 9,7
bilhões" como uma frase no meio de um documento, o robô vai somar errado, e vai
citar o número do ano passado achando que é o de agora.

**Número vai para uma planilha (banco de dados), e o sistema faz a conta na
hora.** Aí ele nunca erra e nunca fica velho sem avisar.

**Texto de contrato, sim, vira busca** — porque "o que a cláusula 4.2 quer
dizer" não tem uma resposta única, é interpretação.

### A regra de multi-agente

Antes eu escrevi *"paralelize leitura, serialize escrita"*. Traduzindo:

**Vários robôs podem LER ao mesmo tempo** — é assim que a gente destilou 8.800
conversas em uma noite, com vários trabalhando em paralelo.

**Mas só UM pode ESCREVER.** Se dois robôs mexem na mesma apólice ao mesmo tempo,
um desfaz o outro e ninguém percebe.

**Na prática, para nós:** os subagentes que leem e analisam **nunca** podem
alterar dado de cliente. Isso vira uma trava no sistema, não uma recomendação.

### E a terceira: quem confere não pode ver quem fez

Descobrimos, com dado de produção de outra empresa, que **um revisor que não vê
o raciocínio do autor pega ~2 erros por revisão, 58% deles graves** — e que ele
funciona **pior** se você mostrar a ele o que o autor pensou.

**Na prática:** quando o sistema afirmar "essa apólice cobre X", um segundo robô
recebe **só a afirmação**, vai buscar sozinho no acervo, e tenta **derrubar**.
Se não achar prova, a afirmação é rebaixada de "fato" para "suposição".

**É o que impede o sistema de prometer cobertura que não existe.**

---

## Sobre entrar nos portais das seguradoras

Você perguntou o que a pesquisa ajuda na prática. Três coisas:

**1. A parte difícil não é ler — é entrar.** Os robôs de navegador do mundo
acertam mais de 70% quando é só ler, e caem para 46% quando é preencher. E a
maior parte das falhas **não é o robô ser burro: é bloqueio de login, CAPTCHA e
detecção de robô.** Ou seja: quando formos abrir a segunda, terceira e décima
seguradora, o esforço vai estar no acesso, não na leitura.

**2. É prática estabelecida no mercado brasileiro.** A Segfy — concorrente de
sistema de gestão, com 30 anos — diz **abertamente no site** que faz cotação de
três formas: *"API, extensão e robô"*. **Isso não nos dá permissão contratual,
mas mostra que não estamos inventando nada** — é o padrão do setor.

**3. Existe um caminho legal e melhor, e ele é regulado.** Chama **Open
Insurance** (Circular SUSEP 635/2021). É o "Open Banking do seguro": com
autorização do cliente, a seguradora é **obrigada** a entregar apólice, sinistro
e cotação por uma via oficial e auditada.

**E o detalhe que decide:** *"corretoras habilitadas na SUSEP podem atuar como
processadoras de ordem do cliente"*. **A corretora pode ser um participante
oficial do Open Insurance.**

**Isso divide o problema em dois, e a divisão é limpa:**

```
dado do CLIENTE (apólice, sinistro) ...... pelo Open Insurance, oficial e legal
dado da CORRETORA (comissão) ............. não tem via oficial — aqui robô é a
                                           única opção, e o risco é menor:
                                           é a senha dela, sobre o dado dela
```

---

## As decisões que são suas — e o que cada uma ganha ou arrisca

| Decisão | Se sim, ganha | Se não, perde |
|---|---|---|
| **Habilitar como participante do Open Insurance** | via legal para apólice de cliente, sem robô e sem risco de bloqueio | continuamos dependendo de robô para tudo |
| **Usar a tabela FIPE pelo caminho interno** | validação de valor de graça | tem que pagar (~R$ 10 mil) ou licenciar |
| **Baixar em massa as Condições Gerais** | acervo completo do país | é agressivo contra servidor público — recomendo baixar só o que a corretora vende |
| **Comparar corretoras entre si** (ex.: "a Porto demora o dobro") | o dado mais difícil de copiar que existe | conflita com a política que você assinou em 14/07 |
| **Guardar dados pessoais das bases públicas** | prospecção mais rica | LGPD |

**Nenhuma delas bloqueia começar.** Todas podem ser decididas depois.

---

## Onde estão os documentos

```
docs/canon/pesquisa/
├── 00-LEIA-PRIMEIRO.md ........... este arquivo
└── 01-ACHADOS-COMPLETOS.md ....... o detalhe técnico: URLs, números,
                                    armadilhas, tudo verificado

docs/canon/
├── ESTADO-DA-CAMPANHA.md ......... o estado da destilação de conhecimento
├── AUDIOS-RESGATE.md ............. o que fazer com os áudios amanhã
└── INFOCAP-CORPAPI-MAPA.md ....... o que a API da InfoCap dá e não dá
```
