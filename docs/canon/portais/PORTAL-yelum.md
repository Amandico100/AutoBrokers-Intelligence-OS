# PORTAL YELUM — Novo Meu Espaço Corretor — o mapa do território

> Um arquivo por seguradora. Serve **cobrança, renovação e cotação** — as seções
> 1 a 4 e a 6 valem para os três; a 5 separa o que já roda do que só está anotado.
>
> **Leia a [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md) antes de mexer
> aqui.** Ela define o método das 5 fases e o teto de visitas.
>
> Estado: 🟢 **FASES 1–4 FECHADAS** · a journey rodou contra o portal real e
> trouxe o boleto certo · 68 asserções verdes · falta a Fase 5 (fila de produção)
> Última medição: 12/08/2026 · corretora **Resulta**

| Marca | Significado |
|---|---|
| 📊 | medido — no HAR, no HTML ou em visita real, com data |
| ❓ | **não medido** |
| 🔴 | trava séria |
| 🚫 | o robô nunca toca |

---

# 1. A PORTA

## 1.1 🔴 O portal MUDOU de endereço — e o link novo não pode ser guardado

📊 O portal antigo saiu do ar; o atual é o **Novo MEC**:

```
portal   https://novomeuespacocorretor.yelumseguros.com.br/
login    https://novomeuespacocorretor.yelumseguros.com.br/account/login
```

O `/account/login` redireciona sozinho para um **Auth0** em outro host:

```
https://auth-broker.yelumseguros.com.br/login?state=…&client=VWTmKOHt…
       &protocol=oauth2&response_type=code&scope=openid email profile offline_access
       &redirect_uri=…/openid-connect/generic
```

> 🔴 **Esse link comprido não serve para guardar.** O `state` é um valor de uso
> único que o Auth0 emite e expira em minutos — gravá-lo no cadastro faria o
> robô entrar hoje e falhar amanhã, com um erro que parece credencial errada.
> O que fica gravado é o `/account/login`, que gera um `state` novo a cada vez.

## 1.2 🔴 O formulário nasce por JavaScript

📊 Campos do Auth0, medidos:

```
input[name=username]              usuário
input[name=password]#1-password   senha
button[type=submit]               "Continuar para o Portal"
```

Eles **não existem** no HTML inicial. Espera-se o **campo**, nunca o relógio —
foi o que custou uma visita na Tokio, e aqui já nasceu certo.

## 1.3 🔴 Akamai também aqui — e eu havia dito que não

📊 Confirmado no HAR do app logado:

```
GET  /8tgyDHgjv/…/wgAYBcB     560 KB de JS com a marca `bmak`
POST /8tgyDHgjv/…/wgAYBcB     {"sensor_data":"3;0;1;0;4272688;…"}  -> {"success": true}
GET  s.go-mpulse.net/boomerang/…                       (Akamai mPulse)
```

> **Eu afirmei ao Founder que a Yelum não tinha trava nenhuma. Estava errado.**
> Na sondagem eu carreguei `novomeuespacocorretor…/home` — a **página pública
> de marketing** — e concluí sobre o **app logado**. São coisas diferentes, e a
> pública não é protegida.
>
> É o mesmo erro de método que já aconteceu duas vezes neste projeto: medir uma
> coisa **vizinha** da que se afirma. A pergunta que teria pego:
> *"a página que eu carreguei é a mesma sobre a qual eu vou afirmar?"*

O conserto já existia e é o que faz esta journey entrar: `--headless=new`
(impressão digital em JS) + **User-Agent limpo** (o cabeçalho).

## 1.4 Sem CAPTCHA · teto de visitas ainda não medido

📊 Nenhuma tela pediu CAPTCHA, nem na sondagem nem nas 4 visitas reais.
❓ O teto de frequência **não foi medido**. Tokio travou em ~4 e HDI em ~15.
Até medir, trate como a Tokio (o mais restritivo) — é o lado seguro.

## 1.5 O login vale para as DUAS marcas do grupo

📊 O rodapé e o topo do portal levam a `hdi.com.br/hdidigital` — a Yelum e a
HDI são o **mesmo grupo** (a API se chama `integracao.grupohdiseguros.com.br`).
❓ Não medido se a credencial atravessa. Se atravessar, é uma porta a menos.

---

# 2. A TOPOLOGIA — e onde mora a API

📊 O portal é **Drupal** servindo blocos React. Os dados vêm de uma API REST em
outro host, declarada no próprio HTML:

```json
"api_url_prefix": "https://integracao.grupohdiseguros.com.br/agent-portal-brazil"
```

## 2.1 🔴 O token NÃO está em lugar nenhum que dê para procurar

📊 Depois do login eu varri `localStorage` e `sessionStorage` **inteiros**:
15 chaves (`portalMenus` 66 KB, `manager-contact-data` 269 KB, `get-user-data`,
`userShortcuts`…) — **nenhuma com JWT**. O Auth0 SPA guarda o access token
**em memória**, que é a prática recomendada dele.

E o `Authorization` **não aparece no HAR**: o Chrome o remove junto com os
cookies ao exportar. Quem denuncia que ele existe é o **preflight**:

```
access-control-request-headers: authorization,content-type
```

📊 Interceptando a requisição do próprio app: `Authorization: Bearer <JWT de
1.758 caracteres>`.

> **Então a journey não procura o token: ela escuta.** Abre uma tela, deixa o
> app fazer a chamada dele, captura o cabeçalho e reusa. É a SPEC-033 levada um
> passo adiante — a página não só fala a língua, ela empresta a credencial.

## 2.2 🔴 E a tela que se escuta é o DASHBOARD, não a de parcelas

📊 Custou uma visita. `/lp/payment-management` abre dizendo *"Você ainda não
realizou nenhuma busca"* — **não chama a API sozinha**, espera o clique em
Buscar. Escutando ali, o token nunca aparece.

O **dashboard**, sim: monta os cartões de pendência e para isso dispara sete
endpoints, todos com `Authorization`. É a página que fala sem ninguém pedir.

📊 Os sete, do `/api/dashboard-user-cards/list`:

```
POST /policy/policiestoexpirecount        Apólices a vencer
GET  /policy/countpolicycanceled          Apólices canceladas
GET  /inspection/incomplete?filter=count  Vistoria Prévia Frustrada
GET  /dashboard/dso/count                 DSO pendentes
POST /proposal/totaldeclinedproposals     Propostas recusadas
GET  /payment/installment/overdue?filter=count   Parcelas Atrasadas
POST /proposal/totalpendingproposals      Propostas pendentes
```

## 2.3 ⚠️ `credentials: 'include'` QUEBRA as chamadas

📊 O preflight autoriza a origem:

```
access-control-allow-origin   https://novomeuespacocorretor.yelumseguros.com.br
access-control-allow-methods  GET, PUT, POST, DELETE, OPTIONS
access-control-allow-headers  *
```

**Mas não manda `Access-Control-Allow-Credentials`.** Com `include`, o
navegador recusa com `TypeError: Failed to fetch` — que se parece com queda de
rede e manda investigar no lugar errado. Vai `credentials: 'omit'` + Bearer.

---

# 3. AS ARMADILHAS

## 3.1 🔴 A janela de busca alcança ~90 dias — e para em ONTEM

📊 Da URL da própria tela: `minDate=2026-05-14&maxDate=2026-08-11`, com a busca
feita em 12/08. Ou seja: **90 dias de alcance, e nunca o dia de hoje.**

Uma dívida mais velha que isso **não aparece**. É o mesmo tipo de limite da HDI
(30 dias por bloco), mas aqui não dá para varrer em blocos para trás sem saber
se a API aceita — ❓ a tela limita; se a API limita também, não foi medido.

## 3.2 🟢 A testemunha — a melhor das quatro seguradoras

```
GET  /payment/installment/overdue?filter=count   conta SEM filtro de data
POST /payment/installment/search-by-brokerlist   traz SÓ a janela pedida
```

> **As duas fontes são independentes.** Se o contador diz 9 e a janela trouxe 4,
> os 5 que faltam existem — quase certamente vencidos antes do alcance da tela.
> Afirmar "carteira em dia" aí seria a mentira que a SPEC-070 §2 proíbe.

Na Tokio a testemunha vinha no mesmo documento; aqui vem de **outro endpoint**,
o que é melhor: um erro no filtro de data não contamina as duas.

📊 Na visita real: contador `1`, lista `1`. Bateu.

## 3.3 🔴 A MESMA API devolve o valor em DOIS formatos

📊 O mesmo valor, dois endpoints, no mesmo instante:

```
search-by-brokerlist    "Amount": "1.672,62"     ← brasileiro
getPaymentInstallments  "Amount": "1672.62"      ← ponto decimal
```

Um parser que só entende `1.672,62` lê **`1,67`** no outro — erro de mil vezes
num valor de cobrança. `_valor()` entende os dois, e o teste [2] usa os dois
textos reais para provar que dão o mesmo número.

## 3.4 🟠 A data vem como 03:00Z — não converter o fuso

📊 `"DueDate": "2026-08-08T03:00:00.000Z"` é meia-noite de Brasília. Cortar em
10 caracteres preserva o **dia que a tela mostra**; converter o fuso moveria a
data um dia para trás em **toda** parcela.

## 3.5 🔴 O telefone do portal vem VAZIO

📊 Do registro real de `searchCustomerPolicy`, no mesmo objeto:

```
"EmailAddress": "NATHALIA.CAPPELLETTI@…"    preenchido
"TelephoneAreaCode": ""                      VAZIO
"TelePhoneNumber": ""                        VAZIO
```

E a tela confirma: `Telefone —`.

> Terceira seguradora seguida em que o telefone do portal não serve. Na Tokio
> ele **mentia** (a tela calculava um celular); aqui ele simplesmente **não
> existe**. A regra é a mesma: o WhatsApp sai do **sistema de gestão da
> corretora** (InfoCap, Quiver), por `cpf_cnpj`.

## 3.6 🟠 A lista de inadimplentes não traz o documento

📊 `search-by-brokerlist` tem nome, apólice, valor, vencimento — **mas não tem
CPF/CNPJ**. Ele vem de `POST /customer/searchCustomerPolicy` no campo
`CustomerID`, já **limpo** (`46921059000113`, sem pontuação).

Uma chamada a mais por inadimplente. É o preço de ter o WhatsApp certo.

## 3.7 🟠 Grafias erradas da própria Yelum — não "consertar"

📊 `TelePhoneNumber` (P maiúsculo no meio) e `"PolicyRenewed "` (com espaço no
fim da chave). São defeitos da API. Um código que os normaliza para de casar.
A fixture os preserva de propósito.

---

# 4. AS TRAVAS — 🚫 o que o robô nunca toca

| Onde | O que | Por quê |
|---|---|---|
| `Reprogramar` | `/payment/reschedule` | muda a data de vencimento — decisão comercial |
| `Alterar Forma Pagamento` | `simulatepaymentmethodchange` | escreve no contrato |
| `Settle installments` | `simulateinstalmentsettlement` | quita parcela |
| `/lp/invoice` | 2ª via em lote | dispara e-mail de verdade |

📊 E a própria Yelum cobra pela reprogramação — está impresso no boleto:

> *"Havendo aceitação, pela seguradora, para reemissão do boleto com nova data
> para pagamento, poderão ser cobrados **até R$ 50,00** a título de despesa
> operacional."*

> 🔴 Ou seja: reprogramar não é só escrever no contrato — **pode gerar cobrança
> ao segurado**. Mais um motivo para o robô nunca tocar.

📊 E o modal do `Reprogramar` pergunta antes: *"houve sinistro?"* — pergunta que
só uma pessoa pode responder.

---

# 5. OS SERVIÇOS

## 5.1 COBRANÇA 🟢 journey escrita — `portal_worker/journeys/yelum_corretor.py`

### A cadeia — quatro chamadas, nenhuma que escreve

```
1) GET  /payment/installment/overdue?filter=count
   → {"Total": N}                                      a testemunha

2) POST /payment/installment/search-by-brokerlist
        ?&DueDate-gte=…&DueDate-lte=…&size=200&from=0&SearchType=3
        body {"brokerlist":[]}
   → {"total": N, "response": [ … ]}

3) POST /customer/searchCustomerPolicy   {"PolicyNumber": "…"}
   → CustomerID = o CPF/CNPJ limpo

4) GET  /printdoc/policy/{PolicyNumber}/issuance/{IssuanceID}
        ?installmentID={InstallmentID}
   → o PDF do boleto, direto
```

> 🟢 **O boleto é LEITURA.** Não existe "gerar 2ª via", não existe modal, não
> existe data para escolher. As três chaves da URL vêm todas da lista. Na Tokio
> o mesmo resultado custava três chamadas e uma decisão de negócio.

### `SearchType` — lido do `<select>`, não chutado

```
1 = Quitadas      2 = A Vencer      3 = Atrasadas   ← o nosso
```

### As formas de pagamento

📊 De `simulatepaymentmethodchange`, que lista o que a Yelum aceita:

```
FB  Boleto bancário    ← o único que gera boleto
DC  Débito em conta    🚫 retido, vira tarefa humana
CC  Cartão de crédito  🚫 idem
PX  QR Code Pix        ❓ não medido como forma vigente
```

📊 E a lista traz `RejReason` — o motivo da recusa (`SALDO INSUFICIENTE`,
`CARTAO EXPIRADO`), que vai inteiro para a tarefa da atendente.

### O que a lista entrega

```
Status · StatusID · PolicyNumber · IssuanceID · InstallmentID · CustomerName
· ProductName · CommercialProductName · BrokerName · ContractID · Amount
· OriginalAmount · AmountCorrected · Tax (IOF) · DueDate · OriginalDueDate
· ExtDueDate · PaymentModality · PaymentModalityDesc · RejDate · RejReason
```

### 📊 A visita real — 12/08/2026, corretora Resulta

```
login .............. Auth0, 2 campos, entrou
token .............. Bearer, 1.758 chars, capturado no DASHBOARD
contador ........... 200 · Total = 1
lista .............. 200 · declarado 1 · lidos 1 · janela 15/05 a 11/08
cliente ............ 200 · documento 46921059000113  ✓ bate com a tela
BOLETO ............. ok · 5.908 bytes
```

> 🎯 **5.908 bytes é exatamente o tamanho do PDF que o Founder baixou à mão**
> (`BOLETO YELUM doc payment_672520250403934_2_2.pdf`). Byte por byte, o mesmo
> documento — pela mão e pelo robô.

## 5.2 RENOVAÇÃO 📋 conhecimento anotado, sem código

📊 Tudo passa por um **proxy de identidade** que abre o sistema legado da marca:

```
https://identityproxy.yelumseguros.com.br/Identity/SelectUserInfo?SessionType=<TIPO>
```

O relatório de renovação de cada produto:

```
Auto individual   ID:CotadorPL&OriginType=13
Frotas            ID:CotadorPLFrotaFacil&OriginType=13
Residência        ID:CotadorCPLResidenciaMapaRenovacaoPlataforma
Vida              ID:RelatorioRenovacaoVida
Patrimonial       ID:CotadorCPLCS&OriginType=2
Engenharia/RC     ID:CotadorCL&Option=engenharia
Transporte        ID:CotadorCL&Option=transporte
Equipamentos      ID:CotadorCL&Option=equipamentos
Imobiliária       ID:ImobiliariaRenovacao
Equip. agrícolas  https://identityproxy…/Identity?SessionType=CotadorIndianaRenovacao
```

📊 E o **cartão do dashboard** já conta quantas vencem, sem navegar:
`POST /policy/policiestoexpirecount` → tela `/lp/renewal?Period=currentmonth`.

> 🔴 **Diferença importante da Tokio para a Yelum:** aqui a renovação **não** é
> uma tela do portal — é um salto para o sistema legado, com troca de sessão no
> `identityproxy`. Provavelmente não dá para chamar por dentro como a cobrança.
> ❓ Não medido. É o primeiro a medir quando a renovação chegar.

## 5.3 COTAÇÃO 📋 conhecimento anotado, sem código

📊 A Yelum vende sob **quatro marcas**, e cada uma tem cotador próprio:

```
Yelum      ID:CotadorPLLiberty          (repare: "Liberty", o nome antigo)
Aliro      ID:CotadorPLAliro
Affinity   ID:CotadorPLAffinity
Indiana    ID:CotadorPLIndiana
```

Consultar cotação é o mesmo com `&OriginType=9`; endosso com `&OriginType=12`.

Demais produtos:

```
Frotas            ID:CotadorPLFrotaFacil&OriginType=8
Residência        ID:CotacaoResidencia
Vida individual   ID:MeuCotador          · coletivo  ID:CotacaoVidaPlataforma
Patrimonial       ID:CotadorCPLCS
Engenharia/RC     ID:CotacaoEngenharia
Transporte        ID:CotacaoTransporte
Equipamentos      ID:CotadorCL&PaginaInicial=selecionarProduto
Imobiliária       ID:Imobiliaria
```

📊 Únicas telas de cotação **dentro** do portal novo:
`~/lp/quotation-search` (Vida Coletivo) e `~/lp/proposal-search`.

## 5.4 OUTROS SERVIÇOS mapeados

📊 Sinistro: `~/lp/open-claim` · `~/lp/claim-search` · `~/lp/oficinas-referenciadas-dnd`
📊 Consultas: `~/lp/policy-search` · `~/lp/cancellation-search` · `~/lp/policy-details`
📊 Financeiro: `~/lp/payment-management` · `~/lp/invoice` · `~/lp/commissions`
· `~/lp/income-report`
📊 Vistoria: `ID:AgendarVistoriaPrevia` · `ID:VistoriaPrevia` ·
`ID:AgendarVistoriaFrota` · `~/lp/incomplete-inspection`
📊 Assistência: `autoatendimento.facil24h.com.br/Acesso?ClienteInstitucional=241`
· vidros em `abraseuatendimento.com.br/#/yelum/menu-atendimento`
📊 Condições gerais (serve ao **Acervo**):
`https://www.yelumseguros.com.br/Pages/seguros/condicoes-gerais.aspx`
📊 Formulários: `~/lp/formularios` · FAQ: `~/lp/faq`
📊 DSO (o canal de solicitação): `ID:DSO`

---

# 6. DADOS DA TELA que a cobrança NÃO usa

**Da apólice** (`getPolicyDetails`): `ValidityStartDate` · `ValidityEndDate` ·
`TotalPremium` · `EndorsementID` · `ProposalID` · `IssuanceDate` · `IsCanceled`
· `IsAffinity` · `IsDigitalKit` · `BranchID`/`BranchName` · `LineOfBusiness` ·
**`MakeName`** (a marca: Liberty/Aliro/Affinity/Indiana) · `PolicyRenewed ` ·
`PrevPolNbr` — 🔴 os dois últimos são **história de renovação**.

**Do histórico** (`policy/search/history`): cada emissão com
`EndorsementMovementType`, `TotalPremium` e **`InstallmentStatus`**
("Em dia" / "Atrasado") — um resumo de saúde por emissão.

**Do cliente** (`searchCustomerPolicy`): `CustomerID` · `SocialName` ·
`EmailAddress` · vigências.

**Do boleto impresso:** `Nosso Número` · linha digitável · agência/beneficiário
· `MULTA DE 2%` + `0,044% ao dia` · `NÃO RECEBER APÓS <data+15d>` ·
a advertência de cancelamento da apólice.

**Da comissão** (aba Comissão): código do corretor, `% de Participação`,
`% de comissão` — 📊 no caso medido, 100% e 30%.

---

# 7. O QUE FALTA

| # | O que | Quem destrava |
|---|---|---|
| 1 | **Fase 5** — rodar pela fila de produção | 🧑 redeploy do `portal-worker` |
| 2 | A credencial da **AutoFleet** (a da Resulta entra; a outra dá erro) | 🧑 Founder / Saionara |
| 3 | O **teto de visitas** da Yelum — ainda não medido | 🤖 aparece com o uso |
| 4 | Se a API aceita janela **maior que 90 dias** (a tela não aceita) | 🤖 1 chamada |
| 5 | Se a **paginação** (`from`/`size`) é necessária com muitos inadimplentes | 🤖 aparece sozinho |
| 6 | Se a credencial **atravessa para a HDI** (mesmo grupo) | 🤖 1 visita |
| 7 | Se `PX` (Pix) aparece como forma vigente e o que fazer com ela | 🤖 aparece sozinho |

---

# 8. HISTÓRICO

| Data | O que |
|---|---|
| 12/08/2026 | Portal novo (Novo MEC) cadastrado, credencial da Resulta gravada cifrada. **Fases 1–4 fechadas**: API REST descoberta, cadeia de 4 passos medida, journey escrita, 68 asserções verdes, e o boleto real baixado com o **mesmo tamanho em bytes** do que o Founder baixou à mão. 🔴 Achados: o token não está em storage nenhum (só escutando o app) · a tela que fala é o dashboard, não a de parcelas · `credentials: 'include'` quebra por falta de `Allow-Credentials` · a mesma API devolve valor em dois formatos · telefone vem vazio · reprogramar pode custar R$ 50 ao segurado · **e a correção: a Yelum TEM Akamai, eu havia medido a página pública em vez do app.** |
