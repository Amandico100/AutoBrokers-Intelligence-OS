---
> **Status:** canônica · **executável agora** (só fontes públicas)
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Autoridade superior:** CLAUDE.md · SPEC-052 (cérebro) · SPEC-060 (research)
> **Origem:** pesquisa de fontes públicas de 30/07 · verificação à mão do
> repositório SUSEP em 30/07 · campanha de destilação de 29–31/07
> **Branch:** `feat/spec066-acervo-susep-rag`
---

# SPEC-066 — O Acervo: SUSEP, Condições Gerais e o RAG Definitivo

> **A frase que resume:** as Condições Gerais de todo produto de seguro do Brasil
> são públicas, consultáveis por número de processo, sem senha — e devolvem
> **todas as versões com data**. O produto de auto da Allianz mudou **72 vezes**.
> **Vale a versão que estava valendo no dia em que a apólice foi emitida, e a
> mais recente quase nunca é a certa.**

---

## 1. Por que esta SPEC existe

### 1.1 O que foi verificado à mão

**30/07/2026**, requisição real, sem autenticação:

```
POST www2.susep.gov.br/safe/menumercado/REP2/Produto.aspx/Consultar
     multipart/form-data · campo: numeroProcesso

processo 15414.002216/2004-57 (Allianz, Auto-Casco)
   → HTTP 200 · 72.638 bytes · 72 VERSÕES com link de download
   → o PDF baixado tem 138 páginas
```

Sem senha. Sem CAPTCHA. Sem token de sessão.

### 1.2 Por que a data é o fosso, e não o acervo

**Qualquer concorrente consegue baixar PDF. Poucos vão modelar vigência.**

```
apólice emitida em ........... março de 2026
condições mudaram em ......... julho de 2026
sinistro acontece em ......... agosto de 2026

vale a versão de MARÇO
```

Um produto muda 4 a 8 vezes por ano. Uma apólice fica parada 12 meses.
**O intervalo entre a emissão e a mudança seguinte é onde mora o erro** — e um
RAG que indexa só a versão atual **responde errado e não percebe.**

**Correção registrada:** numa apólice renovada, vale a versão vigente na
**emissão da apólice atual** — não a da primeira contratação. Renovou em 2026, é
a de 2026.

### 1.3 A armadilha que zera o número mais importante do setor

No `Ses_seguros.csv` da SUSEP (1.796.041 linhas, série desde 1995):

```
201306:  sinistro_retido = 2.481.933.031    sinistro_ocorrido = 0
201312:  sinistro_retido = 0                sinistro_ocorrido = 3.417.756.304
```

**A coluna viva é `sinistro_ocorrido` — e ela não consta na documentação
oficial.** Quem segue o manual calcula **0,0% de sinistralidade em silêncio.**

Em `SES_UF2` é o inverso: lá `sin_dir` é preenchido.

### 1.4 O que esta SPEC entrega

```
o agente responde sobre a cláusula CERTA daquela apólice, na versão certa
o corretor sabe qual seguradora vai apertar ANTES de ela apertar
o acervo de 8.916 cartas é confrontado contra o contrato escrito
e a busca para de confundir "franquia" com "franquia"
```

### 1.5 O que esta SPEC NÃO faz

| Fora do escopo | Onde vai |
|---|---|
| carteira, InfoCap, detectores de dinheiro | SPEC-065 |
| o catálogo de análises do Descobridor | SPEC-067 |
| memória de agente | SPEC-067 |
| e-mail, Meta, canais definitivos | SPEC-069 |

---

# BLOCO 0 — A auditoria que vem antes de qualquer linha de código

**Obrigatório.**

## 0.1 O que confirmar

### 0.1.1 As fontes ainda respondem?

```
[ ] o repositório de produtos SUSEP responde como respondeu em 30/07
[ ] o download por versão ainda devolve PDF
[ ] o BaseCompleta.zip ainda tem o mesmo nome e a mesma estrutura
[ ] o `Data_Final` do sentinela ainda avança mensalmente
```

### 0.1.2 A regra da coluna morta

```
[ ] sinistro_ocorrido continua sendo a coluna viva no período moderno
[ ] sinistro_retido continua zerado desde 2013
[ ] em SES_UF2, sin_dir continua preenchido
[ ] as 40 variações de UF (27 reais + 13 em minúscula) persistem
```

**Se qualquer uma mudar, o cálculo de sinistralidade muda junto.**

### 0.1.3 Quantos produtos a nossa base realmente usa

```
[ ] extrair os números de processo SUSEP das apólices vivas
[ ] contar produtos distintos
[ ] contar versões vigentes nos últimos 24 meses
```

**Se der muito mais que 400, a estratégia de ingestão muda.**

### 0.1.4 O confronto vale a pena?

```
[ ] pegar 20 cartas do acervo sobre exclusão
[ ] achar a condição geral correspondente
[ ] medir: quantas concordam, quantas divergem, quantas não dá para comparar
```

**Se a taxa de divergência for perto de zero, o Bloco B encolhe.** Se for alta,
é o achado mais valioso da SPEC.

### 0.1.5 O motor de busca precisa mesmo mudar?

```
[ ] montar o conjunto de perguntas ANTES de trocar qualquer coisa
[ ] medir o desempenho atual
[ ] só então decidir se miniCOIL vale
```

**Sem medida antes, não há como provar melhora depois.**

### 0.1.6 As outras fontes passam no teste de valor?

Para cada uma do Bloco D:

```
[ ] que pergunta de negócio concreta ela responde?
[ ] essa pergunta aparece nas 69.150 transcrições?
[ ] o corretor pagaria por ela?
```

**A que não passar nas três, sai.** É a regra do Founder: *"nada de 'Notícias da
Globo' com outro nome."*

## 0.2 O relatório

**✅ confirmado · ⚠️ corrigido · ➕ acrescentado · ❓ em aberto · 🚫 retirado.**
Sem ele aprovado, a execução não começa.

---

# BLOCO A — As Condições Gerais, versionadas por vigência

**Nota 97.** É o que nenhum concorrente pago por seguradora pode copiar.

## A.1 O que existe

`POST .../REP2/Produto.aspx/Consultar` com `numeroProcesso` devolve:

```
Sociedade · RAM (grupo de ramo) · Subramo · Situação do produto
e a TABELA DE VERSÕES, cada uma com:
   data de início de comercialização
   data de fim
   link de download do PDF daquela versão
```

Download: `GET .../Produto.aspx/DownloadConsultaPublica/{id}` → `application/pdf`.

**A chave de junção:** o repositório devolve o código de ramo, que casa com
`ses_gruposramos.GRACODIGO` do SES. **É a ponte entre o texto do contrato e a
estatística de mercado.**

## A.2 A ingestão: universal e sob demanda

**A regra, corrigida a partir da observação do Founder:**

> *"Estamos criando um sistema para todas as corretoras, não para a Resulta e a
> AutoFleet."*

```
✗ ERRADO: "os produtos que a Resulta vende"
✓ CERTO:  "ALGUMA corretora do sistema tem apólice viva desse produto"
```

**Como funciona:**

```
1. a apólice traz o número de processo SUSEP
2. o sistema pergunta: já temos esse produto no acervo?
3. não temos → busca as versões, ingere as vigentes nos últimos 24 meses
4. temos → não faz nada
5. corretora nova entra → o sistema descobre os produtos dela
                          e busca só os que faltam
```

**Cada produto é baixado UMA VEZ para todas.** A condição geral da Porto Auto é
a mesma para toda corretora do país.

**O acervo cresce sozinho, e cresce só com o que é usado.**

## A.3 Quantos, de verdade

```
produtos distintos nas duas corretoras piloto ..... 40 a 80 (estimado)
versões vigentes nos últimos 24 meses ............. 3 a 6 por produto
                                                    ─────────────────
                                                    200 a 400 PDFs
```

**Não 510 mil.** Aquele número é o acervo histórico do país inteiro desde 2012, e
**não há razão para tê-lo.**

## A.4 O que NÃO fazer

**FATO medido:** o acervo é enumerável por id sequencial — ~510 mil documentos,
~230 GB, sem autenticação, sem limite de taxa observado. Dez requisições de teste:
**100% de sucesso, 0,19 a 0,79s, ~450 KB médios.**

> **Varrer isso seria tecnicamente trivial e operacionalmente agressivo contra
> servidor de órgão público.**

**Decisão canônica:** ingestão dirigida. **Varredura em massa exige decisão
explícita do Founder registrada em `FOUNDER-DECISIONS.md`.**

## A.5 O modelo temporal

O que precisa existir para a resposta ser certa:

```
produto ......... número de processo SUSEP, sociedade, ramo
versão .......... início de comercialização, fim, o PDF, o hash
cláusula ........ o pedaço de texto, com a versão a que pertence
```

**E a consulta é sempre:** *"para a apólice X, emitida em DD/MM/AAAA, qual a
versão vigente naquela data?"* — nunca *"qual a versão atual?"*.

## A.6 O limite de cobertura, declarado

O sistema da SUSEP só tem produtos **comercializados em 2012 ou criados depois**.
Planos anteriores não migrados exigem pedido pela via de acesso à informação.

**Isso vira mensagem honesta:** quando a apólice for de produto anterior a 2012, o
agente **diz que não tem a condição geral** — nunca usa a de outro produto.

## A.7 Testes

| # | Prova |
|---|---|
| A1 | busca por processo devolve todas as versões, com data |
| A2 | a versão escolhida é a vigente na emissão, não a mais recente |
| A3 | apólice renovada usa a versão da renovação, não a da primeira contratação |
| A4 | produto já no acervo não é baixado de novo |
| A5 | corretora nova só busca o que falta |
| A6 | produto anterior a 2012 gera resposta honesta de ausência |
| A7 | não existe caminho de varredura em massa no código |

---

# BLOCO B — A curadoria pelo plano Max, e o confronto

**Nota 95.** Custo de API: zero.

## B.1 O método, que já foi provado

**8.800 conversas destiladas em 8.916 cartas, por US$ 0,00 de API.**

```
exportar ....... mascarado, direto do banco
destilar ....... subagente lê e escreve as cartas
aplicar ........ script grava, o publicador existente indexa
```

**O mesmo caminho serve para condição geral** — muda a fonte, não o motor.

**Regra herdada, inegociável:** o `templatize` de produção é o único portão de
PII, importado e nunca reimplementado (CLAUDE.md §5).

## B.2 O que se destila de uma condição geral

```
exclusões ........... o que NÃO cobre, e por quê
carências ........... quanto tempo até valer
franquias ........... a FORMA (percentual? valor mínimo?), nunca o número
                      — o número é da apólice
documentos .......... o que a seguradora exige em cada situação
prazos .............. os que são do CONTRATO, não os da operação
definições .......... "súbito e imprevisto", "conteúdo", "área comum"
```

**A regra da campanha, mantida:** carta que fixa percentual, valor ou prazo que
varia por apólice **não entra**. A carta ensina onde verificar.

## B.3 O confronto — o que ninguém mais pode fazer

**Temos os dois lados:**

```
8.916 cartas ......... destiladas de atendimento REAL
a condição geral ..... o que o contrato DIZ
```

**Onde o atendimento contradiz o contrato, uma das duas está errada.**

Três desfechos possíveis, e os três valem:

| Desfecho | O que significa | O que fazer |
|---|---|---|
| **a carta está errada** | o atendente informou errado, e nós aprendemos errado | corrigir a carta, e a corretora precisa saber |
| **a condição mudou** | a carta descreve a versão antiga | versionar a carta |
| **a prática diverge do contrato** | a seguradora faz diferente do que escreveu | **é o achado mais valioso de todos** — vira argumento |

**O terceiro caso é ouro puro:** *"a condição geral diz X, mas em 14 atendimentos
reais a seguradora fez Y."* Isso é evidência de prática, e nenhum concorrente
tem os dois lados.

## B.4 A ordem do confronto

Não confrontar tudo. **Começar pelo que dói:**

```
1. exclusões ......... onde a negativa acontece
2. documentos ........ onde o prazo se perde
3. carências ......... onde a promessa falha
4. o resto ........... depois, se valer
```

## B.5 Testes

| # | Prova |
|---|---|
| B1 | carta destilada de condição geral não fixa número que varia por apólice |
| B2 | o `templatize` de produção é importado, não reimplementado |
| B3 | toda carta de condição geral aponta produto e versão |
| B4 | divergência entre carta e contrato é registrada, com os dois lados |
| B5 | carta corrigida despublica a antiga do índice, não só do banco |

---

# BLOCO C — A sinistralidade e a regra de ingestão

**Nota 94.**

## C.1 O que o SES entrega

```
BaseCompleta.zip .......... 542,6 MB · 2,65 GB descompactado · 40 CSVs
                            atualização SEMANAL · dado avança MENSALMENTE
                            defasagem ~2 meses · latin-1 · separador ;

Ses_seguros.csv ........... 135 MB · 1.796.041 linhas
                            empresa × ramo × mês · série 199501 → hoje

SES_UF2.csv ............... 464 MB · 9.839.005 linhas
                            empresa × ramo × UF × mês · série 200301 → hoje
```

## C.2 As três armadilhas

**C.2.1 — A coluna morta.** `sinistro_retido` zerado desde 2013. A viva é
`sinistro_ocorrido`, **que não consta na documentação.**

**C.2.2 — As UFs em minúscula.** `SES_UF2.UF` tem **40 valores distintos** — 27
reais e 13 duplicatas em minúscula (`pe`, `ce`, `rn`). **`GROUP BY UF` sem
`UPPER()` racha estado em silêncio.**

**C.2.3 — O arquivo descontinuado.** `Ses_rmovram.csv` (294 MB) é marcado
**"descontinuada desde 2014"**. Não ingerir.

**E um cuidado de PII:** `ses_contatos.csv` (143 MB) e `Ses_Administradores.csv`
(41 MB) são **nomes de pessoas**. Não entram.

## C.3 A regra de ingestão — vale para toda fonte

> A pergunta certa não é *"muda todo mês?"*. É **"quem é a autoridade sobre o
> número?"**

```
NÚMERO .......... TABELA, consultada por SQL determinístico
                  nunca texto no RAG

CLÁUSULA ........ RAG, particionado por versão de vigência

IDENTIDADE ...... AO VIVO
```

**Por que número não vai para o RAG:** embutir `R$ 37.068.728.112` num pedaço de
texto é convidar o modelo a errar aritmética e a citar número velho sem saber.

**E não adianta "consultar ao vivo":** o dado nasce com **dois meses de
defasagem**. Não existe sinistralidade de hoje.

## C.4 A detecção de mudança

**Medido:** `HEAD` para o ETag e, se mudou, ler **apenas** o sentinela
`Data_Final` de dentro do zip por range request.

```
6 requisições · 3.398 bytes · 0,0006% do arquivo
```

O arquivo muda toda semana; o dado avança uma vez por mês. **Isso elimina 3 de
cada 4 ingestões completas.**

## C.5 O que a sinistralidade permite dizer

```
"A Allianz fechou o trimestre com 69,3% em auto contra 57,7% da Porto.
 Acima de 65% a seguradora aperta subscrição e sobe preço em 2 a 4 meses.
 Você tem N apólices dela renovando nessa janela."

"Sua carteira na Tokio tem 41% de sinistralidade contra 63% da média Tokio
 no seu estado. Você entrega risco 22 pontos melhor e recebe a mesma
 comissão de todo mundo."
```

**O segundo é argumento de mesa que nenhum corretor tem** — e depende do Bloco C
desta SPEC **mais** a carteira da SPEC-065.

## C.6 Testes

| # | Prova |
|---|---|
| C1 | a sinistralidade usa `sinistro_ocorrido`, não `sinistro_retido` |
| C2 | UF é normalizada — o teste procura estado rachado |
| C3 | o arquivo descontinuado não é ingerido |
| C4 | arquivos com nome de pessoa não são ingeridos |
| C5 | a detecção por sentinela evita reingestão quando o dado não avançou |
| C6 | nenhum número do SES aparece como texto no RAG |

---

# BLOCO D — As outras fontes, com o filtro de valor

**Regra do Founder, aplicada:** *"o que não gerar valor real não entra. Nada de
'Notícias da Globo' com outro nome."*

## D.1 O teste que cada fonte tem de passar

```
1. que pergunta de negócio CONCRETA ela responde?
2. essa pergunta aparece nas 69.150 transcrições ou na operação real?
3. o corretor pagaria por ela?
```

**Não passou nas três, não entra.**

## D.2 As candidatas, e meu voto

| Fonte | Responde | Voto |
|---|---|---|
| **ANS — reajuste real por contrato** | *"a operadora me oferece 17%; quanto ela aplicou em contratos do mesmo porte, mesma UF, mesmo ciclo?"* | **ENTRA** — não tem equivalente no lado de seguros, e é poder de negociação direto na renovação de PME |
| **CNPJ Receita** | *"quais dos meus clientes PF abriram empresa no último ano?"* | **ENTRA** — mas depende da carteira (SPEC-065). Fica pronto e espera |
| **API pública de corretores SUSEP** | *"o registro deste corretor está ativo?"* | **ENTRA** — barata, ao vivo, sem chave, e resolve conformidade e enriquecimento por CNPJ |
| **Criminalidade por município** | *"o bairro do meu cliente piorou e o preço vai subir?"* | **ESTUDAR** — só RJ e SP têm dado municipal; o resto é por UF. Cobertura desigual demais para prometer |
| **FIPE** | validação de valor na emissão | **DECISÃO DO FOUNDER** — a API interna funciona, mas eles declaram publicamente que não oferecem API nem download |
| **Boletins e relatórios setoriais** | contexto de mercado | **NÃO ENTRA** — é o "Notícias da Globo" desta lista |

## D.3 Sobre a FIPE

**O conflito, declarado:**

```
a API interna funciona: 307 tabelas mensais, sem autenticação
a FIPE declara no site: "NÃO disponibilizamos download de qualquer tipo de
                         arquivo... NÃO disponibilizamos serviço de API"

alternativas: parallelum (grátis, 500 req/dia — não sustenta carteira)
              fipe.api.br (CSV completo no plano Pro; export sob medida
                           ≈ R$ 10.000)
```

**É conflito canônico e decisão comercial.** Não codifico nada sobre isso sem
decisão registrada.

**Mas registro o valor:** sem FIPE não existe o cálculo de **taxa efetiva de
renovação** — *"o prêmio subiu 23% e o carro caiu 11%"* — que é a análise de maior
valor do catálogo do Descobridor.

## D.4 Testes

| # | Prova |
|---|---|
| D1 | toda fonte ingerida tem a pergunta de negócio declarada |
| D2 | fonte sem consumidor não é ingerida |
| D3 | cobertura desigual é declarada ao corretor, nunca escondida |

---

# BLOCO E — O motor de busca

**Nota 90. E com uma trava: nada muda antes de medir.**

## E.1 O que temos, verificado

```
denso ........... text-embedding-3-small        (jan/2024, tier barato, inglês)
esparso ......... Qdrant/bm25                   (estatístico puro)
rerank .......... rerank-multilingual-v3.0      (Cohere, 2024, POR CONSULTA)
```

**E as cartas não passam pelo fatiador** — entram como pedaço atômico, com
prefixo de contexto. Isso está certo e não muda.

## E.2 O conjunto de perguntas — vem PRIMEIRO

```
~200 perguntas reais de corretor
cada uma com a carta que DEVERIA aparecer
medir o desempenho atual ANTES de trocar qualquer coisa
```

**Sem isso, todo upgrade é fé.** E a casa já existe: os avaliadores estão em
`services/evals/`.

**De onde vêm as perguntas:** das 69.150 transcrições. São perguntas que segurados
e corretores realmente fizeram — não inventadas.

## E.3 miniCOIL no lugar do BM25

**A razão é o nosso domínio:**

```
franquia ..... dedutível, ou franchising?
prêmio ....... o que se paga, ou o que se ganha?
sinistro ..... o evento, ou o adjetivo?
```

**BM25 é estatístico e não distingue nenhum dos três.** miniCOIL distingue — é
busca esparsa que entende sentido de palavra.

**E já está dentro do Qdrant que rodamos.** Não é dependência nova: são dois
pontos de troca no código.

## E.4 O reranker

Hoje pagamos Cohere **por consulta**, em todos os tenants, **e mandamos texto do
cliente para fora.**

`bge-reranker-v2-m3` é Apache-2.0, multilíngue, self-hosted. **Sem custo por
consulta e sem dado saindo daqui.**

**Mas:** só troca se o conjunto de perguntas provar que não piora.

## E.5 O que NÃO fazer

```
✗ GraphRAG sobre as cartas — existe para pergunta temática sobre corpus;
                             a nossa é busca local, e o que temos já ganha
✗ trocar o modelo denso sem medir — muda a dimensão e obriga coleção nova
✗ produto de memória de terceiro — SPEC-067 trata memória, e a auditoria
                                   mostrou que os benchmarks do setor são
                                   marketing
```

## E.6 Testes

| # | Prova |
|---|---|
| E1 | o conjunto de perguntas existe e tem ao menos 200 |
| E2 | a medida "antes" está registrada |
| E3 | nenhuma troca de modelo entra sem medida "depois" melhor |
| E4 | as cartas continuam entrando como pedaço atômico com prefixo |
| E5 | rerank self-hosted não piora o conjunto |

---

# BLOCO F — O uso prático

**Este bloco existe porque o Founder disse, com razão:**

> *"Não consigo enxergar muito valor na prática. A corretora não vai ficar de
> boca aberta com uma descoberta no meio de 15.000 apólices."*

**Ele está certo.** Acervo sem momento de uso é biblioteca bonita. **Cada peça
desta SPEC precisa caber num momento real — e o que não couber, não entra.**

## F.1 Os cinco momentos

### F.1.1 · O segurado pergunta se tem cobertura

**Onde:** WhatsApp, durante o atendimento.
**O que muda:** hoje o agente responde pelo RAG de atendimento, que sabe o que
**costuma** acontecer. Com a condição geral versionada, ele responde o que o
**contrato daquela apólice** diz.

> *"A apólice dele é de fevereiro de 2024. **Naquela versão**, vazamento por
> corrosão de tubulação embutida era excluído. A versão de 2026 passou a cobrir.
> Como a apólice é da antiga, esse sinistro será negado — e o argumento para
> pedir reanálise está na cláusula 4.2."*

**O valor:** a diferença entre prometer o que a apólice não cobre — e perder o
cliente no pior momento — ou saber antes.

### F.1.2 · O corretor vai negociar com a seguradora

**Onde:** reunião com o gerente de contas, uma ou duas vezes por ano.
**O que muda:** ele chega com número em vez de impressão.

> *"Sua carteira na Tokio tem 41% de sinistralidade contra 63% da média dela no
> seu estado. Você entrega risco 22 pontos melhor e recebe a mesma comissão de
> todo mundo."*

**O valor:** dois pontos de comissão sobre a produção anual dela, num pedido de
trinta minutos. **A seguradora entende essa linguagem, e nenhum corretor chega
com esse número.**

### F.1.3 · A seguradora vai apertar, e ele não sabe

**Onde:** proativo, mensal, quando a SUSEP publica.

> *"A Allianz fechou o trimestre com 69,3% em auto. Acima de 65% a seguradora
> aperta subscrição e sobe preço em 2 a 4 meses. Você tem 214 apólices dela
> renovando exatamente nessa janela."*

**O valor:** antecipar a migração de parte da carteira, em vez de 214 clientes
receberem susto de preço ao mesmo tempo.

### F.1.4 · O sinistro foi negado

**Onde:** no momento mais tenso da relação.
**O que muda:** o agente sabe **qual cláusula** foi usada, **em qual versão**, e
se ela realmente se aplica àquela apólice.

> *"A negativa cita a cláusula de desgaste natural. Na versão vigente na apólice
> dele, essa cláusula tem uma ressalva no parágrafo 3 que se aplica ao caso —
> aqui está o texto para o pedido de reanálise."*

**O valor:** é a conversa que decide se o cliente fica ou vai embora.

### F.1.5 · A prática diverge do contrato

**Onde:** achado do confronto do Bloco B.

> *"A condição geral da [seguradora] diz que o prazo é X. Em 14 atendimentos
> reais dos últimos 6 meses, ela praticou Y. **Isso é argumento.**"*

**O valor:** nenhum concorrente tem os dois lados — nem quem só tem o contrato,
nem quem só tem o atendimento.

## F.2 A regra que este bloco impõe ao resto da SPEC

```
toda peça do acervo declara em QUAL dos cinco momentos ela é usada
peça sem momento não é ingerida
e o momento é testável: existe uma pergunta real que a exercita
```

## F.3 Testes

| # | Prova |
|---|---|
| F1 | toda fonte ingerida aponta ao menos um momento de uso |
| F2 | cada momento tem ao menos uma pergunta real do conjunto que o exercita |
| F3 | a resposta sobre cobertura cita produto, versão e data de vigência |
| F4 | o agente nunca cita cláusula de versão diferente da apólice |
| F5 | quando não há condição geral disponível, ele diz — não improvisa |

---

# 2. Migrations

| Migration | O que faz |
|---|---|
| `..._066_01_produtos_susep.sql` | produto, versão, vigência, hash do PDF |
| `..._066_02_clausulas.sql` | cláusula com vínculo de versão |
| `..._066_03_ses_mercado.sql` | tabela de mercado por empresa, ramo, UF, mês |
| `..._066_04_divergencias.sql` | carta × contrato, com os dois lados |
| `..._066_05_conjunto_de_perguntas.sql` | as ~200 perguntas com resposta esperada |

Todas idempotentes, expand-first, com APPLY/VERIFY/ROLLBACK escritos antes.
**Ler `MIGRATIONS-AUTHORITY.md` antes de qualquer SQL.**

---

# 3. Gate final

```
[ ] o relatório do Bloco 0 aprovado
[ ] os 7 testes do Bloco A        [ ] os 3 testes do Bloco D
[ ] os 5 testes do Bloco B        [ ] os 5 testes do Bloco E
[ ] os 6 testes do Bloco C        [ ] os 5 testes do Bloco F
[ ] a suíte inteira verde
[ ] o conjunto de perguntas com a medida antes e depois
```

## 3.1 A prova viva

```
1. pegar uma apólice real, com data de emissão
2. perguntar sobre uma exclusão
   → a resposta cita produto, versão e data — e é a versão certa
3. mudar a data da apólice para depois de uma mudança de versão
   → a resposta muda
4. perguntar sobre produto anterior a 2012
   → diz que não tem, e não improvisa
5. calcular a sinistralidade de uma seguradora
   → o número bate com o cálculo manual sobre o CSV
6. rodar o conjunto de perguntas
   → o resultado é igual ou melhor que a medida "antes"
```

---

# 4. Riscos

| Risco | Mitigação |
|---|---|
| a SUSEP mudar o repositório | detecção por hash; falha visível, nunca silenciosa |
| ingerir demais e encher o RAG | só produto com apólice viva; teto por corretora |
| a versão errada ser escolhida | teste com data de emissão variável (prova viva §3) |
| número virar texto no RAG | teste procura número do SES dentro de carta |
| troca de modelo piorar a busca | conjunto de perguntas com medida antes e depois |
| varredura em massa por engano | não existe caminho no código; teste prova |
| PII entrar pelas bases da SUSEP | arquivos com nome de pessoa não são ingeridos |

---

# 5. O que NÃO pode acontecer

```
✗ varredura em massa do repositório SUSEP sem decisão registrada
✗ número do SES como texto dentro de carta
✗ cláusula sem vínculo de versão
✗ responder cobertura com versão diferente da apólice
✗ segundo pipeline de ingestão ao lado do que existe
✗ trocar modelo de busca sem medida antes e depois
✗ fonte ingerida sem momento de uso declarado
```
