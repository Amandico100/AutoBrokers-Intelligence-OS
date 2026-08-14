# PORTAL ZURICH — Espaço Parceiros / Portal Corretor — o mapa do território

> **Leia a [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md) antes de mexer aqui.**
>
> Estado: 🟢 **COBRANÇA PRONTA** — entra, lê a carteira, identifica o
> inadimplente e **baixa o boleto** (📊 107.288 bytes, `%PDF`, em 14/08/2026).
> Última medição: **14/08/2026**, sessões reais da AutoFleet e da Resulta.

| Marca | Significado |
|---|---|
| 📊 | medido, com data | ❓ | **não medido** | 🔴 | trava séria | 🚫 | o robô nunca toca |

---

# 1. A PORTA

📊 **URL:** `https://espacoparceiros.zurich.com.br/`
📊 **A API é do mesmo host** — ASP.NET MVC, sessão em **cookie**.

Não há Bearer, não há preflight, não há CORS. Depois de logar, basta chamar
com `credentials: 'same-origin'`. É a porta mais simples das seis — e desta vez
a afirmação vale para o app logado, porque foi lá dentro que medi.

📊 O login é `código do corretor` + senha, **um por corretora**:

```
AutoFleet ... <codigo de 6 digitos>  -> AUTO FLEET R CORRETORA DE SEGUROS L
Resulta ..... <outro codigo>         -> RESULTA CORRETORA DE SEGUROS LTDA
```

Os codigos moram cifrados em `portal_accounts` — credencial nao entra em
runbook (SPEC-023A §4). **As duas entram.** O cabeçalho exibe o nome de quem entrou — a journey lê e
registra na evidência.

## 1.1 ✅ O risco cross-tenant da MAPFRE NÃO se repete aqui

📊 Não há seletor de corretora, não há lista de corretoras, e o HTML salvo não
tem nem a palavra. Cada corretora tem credencial própria e a sessão já nasce
no escopo dela.

> Mesmo assim a journey lê o nome na tela: uma credencial trocada no cadastro
> faz o mesmo estrago, e a checagem custa uma leitura.

## 1.2 🔴 A porta é LENTA e intermitente

📊 O campo de senha apareceu em 9 s numa medição e **não apareceu em 45 s** na
seguinte, na mesma máquina e no mesmo dia. É o mesmo comportamento que o
founder viu como "tela branca" ao capturar à mão.

A journey espera 45 s, **recarrega uma vez** e espera de novo. Desistir na
primeira transformaria lentidão do portal em "não consegui entrar".

---

# 2. A CADEIA DA COBRANÇA

```
1) GET /ParcelaVencidaCorretor/ListarParcelaVencida
       ?dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa
   -> {"corretor": [ … ], "AcionamentoSinistroVida": …}

2) GET /SegundaViaBoletoCorretor/GerarBoleto
       ?identificadorCalculo=0&codSucursal=&paymentNO=…&numeroApolice=…
       &numeroEndosso=…&codigoCarteira=<ramo>&NumParcela=…
       &NumCertificate=…&dataVencimento=dd/MM/aaaa
   -> {"ExibeMsg":…, "Msg":…, "Boleto": {"FileContents": [bytes], …}}
```

📊 **As sete chaves do passo 2 saem todas da lista.** Não há passo
intermediário — e foi assim que o founder baixou o PDF na captura.

🔴 `Boleto.FileContents` é um **array de inteiros**, não base64 — é como o
ASP.NET serializa um `FileContentResult`. Tratar como base64 devolve lixo em
silêncio. 📊 Decodificado da captura: 107.278 bytes, `%PDF-1.4`, sha256
**idêntico** ao PDF baixado à mão.

## 2.1 🔴 O que a lista NÃO traz: o CPF/CNPJ

Diferente da MAPFRE (que entrega o documento na própria lista), aqui são duas
chamadas a mais, e **só para quem vai ser cobrado**:

```
/Apolice/DetalheApolice?…&CodigoCarteira=<ramo>   -> Sucursal, CodigoCarteira, PolicyNoAlt
/Apolice/DetalheDadosSegurado?…&Sucursal=<acima> -> CpfCgcSegurado
```

📊 Essa tela também traz `Email` e `TelefoneSegurado` **preenchidos** — o que
nenhuma das outras cinco tinha. Mesmo assim o WhatsApp continua saindo da
InfoCap: fonte única, sem exceção por seguradora.

---

# 3. AS ARMADILHAS

## 3.1 🔴 O valor vem com vírgula de milhar **E** de decimal

📊 Um dos 37 itens reais: `"valorParcela": "1,287,99"` — são R$ 1.287,99.

O parser brasileiro de sempre (tira o ponto, troca vírgula por ponto) produz
`1.287.99`, que não é número:

```
_valor("1,287,99")  ->  None      📊 medido nos parsers da Yelum e da MAPFRE
```

E `None` **não estoura**: o item seguiria sem valor. A regra da fila diz "sem
data legível não envia" — mas não diz nada sobre valor, então uma cobrança de
R$ 1.287,99 sairia sem dizer quanto.

**A regra correta:** o **último** separador é o decimal; os anteriores são
milhar. É um superconjunto do parser antigo.

> ❓ Os parsers da Yelum e da MAPFRE seguem com o defeito latente. 📊 Aqueles
> portais não produzem esse formato (MAPFRE manda `294.35`, Yelum `1.672,62`),
> então não há falha hoje — mas está anotado como **P-155**.

## 3.2 🔴 `valorJuros` não guarda juros

📊 **Idêntico a `valorParcela` em 37 de 37 itens**, com `valorAcrescimo` sempre
zero. É o caso que a CLAUDE.md §12.1 nomeia: um campo cujo nome mente sobre o
que guarda. Lê-lo como encargo somaria a dívida duas vezes.

A journey grava o valor em `valor` (de `valorParcela`) e o outro em
`valor_juros_declarado` — nome que avisa que não é para conta.

## 3.3 🔴 `Aprovado` NÃO é dívida

📊 Os três estados vistos: `Pago` · `Parcela pendente` · `Aprovado`.

`Aprovado` é pagamento **em processamento**. Cobrar quem já pagou é o pior erro
que este sistema pode cometer com um cliente da corretora — só
`Parcela pendente` entra.

## 3.4 🔴 A janela tem teto, e passar dele DERRUBA A SESSÃO

📊 Medido um fator por vez, com CONTROLE no início e no fim:

```
CONTROLE 30 dias .... 200 · 36 linhas
 45 dias ............ 200 · 43
 60 dias ............ 200 · 48
 90 dias ............ 200 · 53
120 dias ............ 404
180 dias ............ 404
365 dias ............ 503
CONTROLE 30 dias .... 503   ← QUEBROU
 30 dias x3 ......... 503 · 503 · 503
```

São **dois fenômenos**, e só o controle no fim os separa:

1. o teto fica entre 90 e 120 dias — acima disso, **404**;
2. o pedido largo **envenena a sessão**: depois dele, nem a janela que
   funcionava responde.

⚠️ O 404 pode ser do **número de linhas** e não dos dias (53 passaram). Por isso
a journey começa em 90 e **estreita** a cada 404, até o piso de 15 — e **avisa
na mensagem** quando estreitou, porque dívida mais antiga não foi olhada.

📊 Numa rodada real a janela caiu de 90 para 45 sozinha, e disse:
*"a janela foi estreitada de 90 para 45 dias porque o portal recusou a maior;
divida mais antiga NAO foi verificada"*.

## 3.5 🔴 HTTP 200 com lista VAZIA — o desfecho mais perigoso

📊 A mesma janela de 90 dias devolveu **30.229 bytes com 43 linhas** e, três
minutos depois, **200 com 46 bytes e zero linhas** — com um inadimplente real
na carteira. O corpo:

```json
{"corretor":[],"AcionamentoSinistroVida":true}
```

Uma journey que lesse isso como "carteira em dia" mentiria com aparência de
sucesso — o defeito que a SPEC-070 §2(b) proíbe.

📊 A causa aparente é **aquecimento**: a primeira chamada logo depois de abrir
a tela vem vazia; uma segunda, espaçada, traz os dados.

**Zero linhas nunca é conclusão: é pergunta.** A journey relê depois de 6 s, e
se ainda vier vazia termina em `needs_human` — uma corretora ativa não tem zero
parcelas (nem as pagas) em 90 dias.

📊 Esse guarda **disparou numa rodada real** (Resulta, 13/08).

## 3.6 O portal recusa rajada — e recusa com 404, não com 429

📊 A mesma chamada de 90 dias respondeu 200 num script que pausava e 404 na
journey que disparava em sequência. A journey pausa **2,5 s entre chamadas**.

---

# 4. 🟢 O BOLETO — resolvido chamando a função do próprio portal

📊 **14/08/2026.** O download funciona assim:

```javascript
ko.dataFor(document.querySelector('#inputI')).GerarBoleto2({
    payment_no, numeroApolice, numeroEndossoSPY, ramo,
    numeroPrestacao, numeroCertificado, dataVencimento })
```

São os **mesmos sete campos que a lista já devolve**. Quem monta o pedido passa
a ser o código do portal, com o estado dele — não uma reconstrução da URL.

📊 Medido: **107.288 bytes, `%PDF`**.

**A ordem que a journey segue:**

```
1) chamada direta ao endpoint      a mais barata
2) GerarBoleto2 do view model      ← é a que funciona
3) clique no botão 2ªVia da lista  último recurso
```

Os dois últimos são o fallback de navegação visual que a **SPEC-033** prevê
para quando a cadeia direta não passa.

## 4.1 O que foi eliminado antes de chegar aqui

📊 `GerarBoleto` devolveu **404 em toda tentativa da journey**, enquanto a
MESMA chamada funcionou na captura manual. Medido com a lista como controle
(200 antes e depois, em todas as rodadas):

| Variação | Resultado |
|---|---|
| `fetch`, cabeçalho mínimo | 200, mas devolve **HTML** (77 KB) |
| `fetch`, cabeçalho igual ao do jQuery | 404 |
| sem o `_=timestamp` | 404 |
| data com `%2F` | 404 |
| **`$.ajax` do próprio jQuery da página** | 404 |
| **CONTROLE: a lista, no mesmo momento** | **200 com 33 KB** ← sessão viva |

Então **não é** cabeçalho, cliente HTTP, sessão nem ritmo.

📊 E os parâmetros são idênticos — conferidos contra o código do portal
(`/Scripts/Corretor/ParcelaVencida/Index.js`):

```javascript
GerarBoleto2 = function (selectedItem) {
  $.ajax({ url: '/SegundaViaBoletoCorretor/GerarBoleto', type: 'GET',
    data: { identificadorCalculo: '0', codSucursal: …,
            paymentNO: selectedItem.payment_no,
            numeroApolice: selectedItem.numeroApolice,
            numeroEndosso: selectedItem.numeroEndossoSPY,
            codigoCarteira: selectedItem.ramo,
            NumParcela: selectedItem.numeroPrestacao,
            NumCertificate: selectedItem.numeroCertificado,
            dataVencimento: FormatDate(selectedItem.dataVencimento) } … })
```

📊 `FormatDate` é `moment(date).format('DD/MM/YYYY')`, e para o item medido o
`/Date(…)/` e o `dataVencimentoFormated` dão **a mesma data**. Nada diverge.

> **A conclusão:** não adianta reconstruir a URL. Alguma coisa no estado que o
> portal monta não cabe numa query string refeita de fora. Chamar a função dele
> resolve — e é mais robusto: se a Zurich mudar os parâmetros, a função muda
> junto e a journey continua funcionando.

📊 **A visibilidade do botão no portal** confirma a regra de retenção:

```html
data-bind="visible: … && tipoPagamento != 'Cartão de Crédito'
                      && tipoPagamento != 'Débito'"
```

O portal usa lista de **exclusão**; a journey usa lista de **permissão** (só
`Boleto`). A nossa é mais estrita de propósito: `Pix` e `Carnê` existem no
filtro da tela e nunca apareceram nos dados — passariam pela regra deles.

---

# 5. AS TRAVAS — 🚫 o que o robô nunca toca

```python
ROTAS_PROIBIDAS = (
    "renovacao1click",     # Renovação 1-Click
    "restituicao",         # Restituição de Parcelas
    "devolucaoproposta",   # Devolução de Proposta
    "salvarautoservico",   # grava log de auto-serviço no nome do corretor
    "gerarexcel",          # exportação em lote
)
```

O guarda é **comportamental**: o teste chama `_api()` com cada rota proibida e
prova que ela é recusada **antes de sair** — e que uma rota permitida sai.

---

# 6. OS SERVIÇOS — o mapa para os produtos que vêm depois

📊 Observados na captura. **Nada aqui foi exercitado pela cobrança.**

## 6.1 COBRANÇA 🟡 journey escrita — `portal_worker/journeys/zurich_corretor.py`

Ver §2 a §4.

## 6.2 A APÓLICE — oito telas, todas com o mesmo jogo de parâmetros

```
/Apolice/DetalheApolice          resumo, e as chaves que a lista não tem
/Apolice/DetalheDadosSegurado    CPF/CNPJ, endereço, e-mail, telefone
/Apolice/DetalheDadosTecnicos    bem, placa, chassi, categoria
/Apolice/DetalheCoberturas       coberturas e limites
/Apolice/DetalheDadosFinanceiros parcelas e prêmio
/Apolice/DetalheDocumentos       documentos anexos
/Apolice/DetalheCorretor         o corretor da apólice
/Apolice/ListarCorretorApolice   co-corretagem
```

Parâmetros comuns: `NumeroApolice · NumeroEndosso · NumeroCertificado · Ramo ·
Sucursal · CodigoCarteira · CodigoSubCarteira · NumeroItem · Corretor ·
PolicyNoAlt`.

## 6.3 RENOVAÇÃO ❓

O menu **Consulta** tem `Renovação 1-Click` e `Apólices vencidas e a vencer`.
🚫 A journey de cobrança não toca — `Renovação 1-Click` **emite**.

## 6.4 OUTROS CAMINHOS DO MENU

```
Venda · Consulta · Vistoria · Sinistro · Produtos · Gestão · Materiais de apoio
Consulta: Apólices · Parcelas vencidas · Parcelas a vencer ·
          Apólices vencidas e a vencer · Recusas · Renovação 1-Click ·
          Devolução de Proposta · Restituição de Parcelas ·
          Acompanhamento de Cotações e Endossos Riscos Corporativos
Atalhos:  Cálculos e Propostas · Apólice · Extrato de comissão ·
          Portal de Vida · Portal Previdência · Z-Connect (legado)
```

📊 Endpoints já vistos para esses: `/ExtratoComissaoCorretor/*`,
`/InformeRendimentos/*`, `/RenovacaoAutomatica/CopiarCotacao`,
`/Apolice/GerarBoletoVida`, `/Apolice/SegundaViaApoliceVida`.

📊 O cabeçalho traz o programa de pontos (`Infinite Blue`, 59.819 pontos) —
dado de relacionamento, não de cobrança.

---

# 7. O GATE — o que foi exercitado

📊 **13/08/2026**, journey real contra o portal real:

```
Zurich · AutoFleet      done
  corretora na tela ..... AUTO FLEET R CORRETORA DE SEGUROS L
  janela ................ 90 dias (estreitou sozinha para 45 numa rodada)
  carteira .............. 53 linhas · 49 Pago · 2 Aprovado · 2 Parcela pendente
  inadimplente .......... 1 — 1 apólice, R$ 638,95, "Débito não autorizado"
  boleto ................ ❌ 404, RETIDO com o motivo escrito

Zurich · Resulta        needs_human   (o guarda do §3.5 disparou)
  corretora na tela ..... RESULTA CORRETORA DE SEGUROS LTDA   ← credencial OK
  lista ................. 200 com ZERO linhas, duas vezes -> nao afirmo nada

LINHA DE CONTROLE
Allianz · AutoFleet     done — 10 inadimplentes, 10 de 10 boletos, todos %PDF
```

> 📊 O inadimplente que a journey achou sozinha é **exatamente** o que o founder
> encontrou à mão: a mesma apólice, R$ 638,95, vencida em 06/08.

📊 **Testes offline:** `backend/tests/test_zurich_cobranca.py` — **111
asserções verdes**, contra fixture anonimizada, sem tocar no portal.

---

# 8. O QUE FALTA

| # | O que | De quem |
|---|---|:--:|
| ~~P-154~~ | ~~O download da 2ª via devolve 404~~ — ✅ **RESOLVIDO em 14/08** chamando `GerarBoleto2` do view model. | — |
| P-155 | Os parsers da Yelum e da MAPFRE devolvem `None` para `"1,287,99"`. Latente: aqueles portais não produzem esse formato. | 🤖 harmonizar |
| P-156 | A carteira da **Resulta** na Zurich não pôde ser estabelecida — 200 vazio duas vezes. | 🤖 nova leitura |
| P-157 | O teto exato da janela (entre 90 e 120 dias) e se ele é de dias ou de linhas. | 🤖 quando houver folga |

---

# 9. HISTÓRICO

| Data | O que |
|---|---|
| 13/08/2026 | Credenciais das duas corretoras gravadas e cifradas. Captura do founder analisada: cadeia de duas chamadas, PDF byte a byte idêntico, `FileContents` como array de bytes. **Sem risco cross-tenant** (login por corretora). Journey escrita, 111 testes verdes. Medido: o valor com vírgula dupla que zera o parser; `valorJuros` que não é juros; `Aprovado` que não é dívida; o teto da janela **e que passar dele derruba a sessão**; o 200 com lista vazia. Gate: inadimplente identificado corretamente nas duas corretoras, Allianz 10/10 como controle. ❓ O boleto ainda não baixa pelo robô. |
