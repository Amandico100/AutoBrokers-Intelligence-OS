# PORTAL MAPFRE — MAPFRE Negócios — o mapa do território

> **Leia a [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md) antes de mexer aqui.**
>
> Estado: 🟢 **COBRANÇA PRONTA** — journey escrita, testada e exercitada contra
> o portal real, com os PDFs conferidos no bucket.
> Última medição: **13/08/2026**, sessão real da AutoFleet.

| Marca | Significado |
|---|---|
| 📊 | medido, com data | ❓ | **não medido** | 🔴 | trava séria | 🚫 | o robô nunca toca |

---

# 1. A PORTA

📊 **URL:** `https://negocios.mapfre.com.br/acesso`
📊 **A API mora noutro host:** `https://dwwngb2iz4xom.cloudfront.net/api/1.0.0`

Angular + Ionic servido por trás de um shell WordPress/Divi. A porta pública
não tem captcha, Akamai, DataDome, Incapsula nem Cloudflare — e desta vez a
afirmação vale para o **app logado**, porque foi lá dentro que medi.

## 1.1 🔴 O modal de privacidade cobre o formulário — e é a "tela branca"

📊 Antes de o login funcionar, nasce por cima:

```html
<ion-modal class="modal-default privacy-policy-modal show-modal">
  <iframe id="privacy-policy_iframe"
          src="https://politica.mapfre.com.br/#/politica-privacidade/mcscolaborador">
```

Ele **intercepta todo clique** (`subtree intercepts pointer events`). E não tem
botão "Aceitar": fecha por um ícone no canto superior direito.

```
ion-modal.show-modal ion-buttons.custom-close-button     ← o que funciona
ion-modal.show-modal .icon-CLOSE                         ← o span dentro dele
```

> 📊 `Escape` **não** fecha. Um dump que procure só `button`/`ion-button`
> devolve lista vazia — foi o que aconteceu na primeira medição.
>
> É quase certamente o que o Founder enfrentou ao capturar à mão, quando "ficava
> em branco e precisava clicar várias vezes".

## 1.2 🔴 O Ionic não escuta quem preenche o campo por fora

📊 `fill()` escreve no `<input>` nativo, mas **não** dispara o `ionInput` que o
Angular ouve. O modelo continua vazio, o botão **Entrar** fica `disabled`, e o
clique estoura por timeout — **sem nunca tentar o login**.

```
u.fill(cpf)                    -> botão continua desabilitado, 0 tentativas
u.press_sequentially(cpf, 55)  -> preenchidos [14, 9], botão habilitado ✅
```

Efeito colateral bom: a medição errada **não gastou tentativa de senha**.

> Os campos continuam sendo selecionados por `type`, nunca por `ion-input-N`
> — 📊 o índice do Ionic é ordem de renderização e muda sozinho. Depois do
> login, os campos do modal seguinte já nascem como `ion-input-2` e `-3`.

## 1.3 O login vai com dígitos, não com pontuação

📊 O `username` da conta guarda **só os 11 dígitos** do CPF. O campo tem máscara
e o exibe com pontuação (14 caracteres na tela — foi assim que confirmei que o
Ionic aceitou o que foi digitado). Digitar a pontuação junto pode duplicar
separador e produzir "credencial inválida" — erro que manda procurar no lugar
errado.

> O CPF em si não é escrito aqui: ele mora cifrado em `portal_accounts`, e
> documento de pessoa real não entra em runbook (SPEC-023A §4).

## 1.4 🔴 São TRÊS tokens, e o certo é o mais novo

📊 O `Authorization` vai **cru**, sem a palavra `Bearer`. E **cresce** conforme
o contexto entra nele:

| chars | nasce quando | serve para |
|---:|---|---|
| 1.481 | carga inicial | `/broker/*` e `/desk` · **401** em `/receipts` |
| 4.710 | depois do `POST /login` | ainda sem corretora · **500** em `/receipts` |
| 7.049 | depois do `POST /brokerCode` | **este** é o de `/receipts` e do boleto |

O de 7.049 carrega `customPayload: {"distributorId": "10754", "tokenTrans": …}`.

> 🔴 Uma journey que capture o **primeiro** `Authorization` — como a da Yelum
> faz, e lá está certo — recebe HTTP 500 sem explicação. Aqui se guarda **o
> mais longo visto**, e só depois da corretora escolhida.

⚠️ `credentials: 'omit'` obrigatório: 📊 o preflight libera a origem (`*`) mas
**não** manda `Access-Control-Allow-Credentials`. Mesma armadilha da Yelum.

---

# 2. 🔴 O CROSS-TENANT — o coração deste portal

## 2.1 Um login enxerga DUAS corretoras, e trocar um campo troca a empresa

📊 Medido em 13/08/2026, com o login da AutoFleet, variando **só** o `brokerId`
do corpo da busca:

```
brokerId=55744776  ->  59 parcelas, 21 clientes   AUTO FLEET R CORRETORA DE SEGU
brokerId=12542146  ->   8 parcelas,  4 clientes   RESULTA CORRETORA DE SEGUROS L
clientes em comum  ->  ZERO
```

> **Quando erra, não erra "quase certo": traz a empresa errada inteira.**

Resulta e AutoFleet são do mesmo dono, separadas por ramo para fins fiscais —
é isso que explica o login compartilhado. **Não é a regra**: nenhuma outra
corretora deve ter isso, e cada uma entra com a credencial dela.

## 2.2 O conserto é DADO, não leitura de tela

📊 O endpoint que o próprio portal usa para montar a lista do modal:

```
GET /api/1.0.0/distributor/{distributorId}/brokers

[{"brokerId": "12542146", "brokerDesc": "RESULTA CORRETORA DE SEGUROS L"},
 {"brokerId": "55744776", "brokerDesc": "AUTO FLEET R CORRETORA DE SEGU"}]
```

A journey casa `portal_accounts.account_label` com `brokerDesc` e exige
**exatamente uma** linha:

```
zero  -> este login não alcança essa corretora        -> needs_human
duas  -> ambíguo; escolher seria adivinhar             -> needs_human
uma   -> é essa, e o brokerId dela vai no corpo        -> segue
```

E há **segunda tranca**: cada linha lida declara o broker dela em
`brokerProductionKey.broker.brokerId`. Se alguma vier de outro, a leitura
inteira é descartada — não se grava metade.

> É testável **offline**, com fixture, sem abrir o portal. Era a maior fraqueza
> do desenho anterior, que dependia de reler a tela.

## 2.3 O `distributorId` NÃO separa as corretoras

📊 É `10754` para as duas. Quem separa é o `brokerId`. E o campo **Código
interno** do modal é uma terceira coisa:

```
TODOS · 111 · 130183 · 1932        todos da MESMA AutoFleet
                                   (agencyDesc: FLORIANOPOLIS - GC DO BRASIL)
```

---

# 3. A CADEIA DA COBRANÇA — duas chamadas

```
1) POST /api/1.0.0/distributor/{did}/receipts
   {brokerId, dateFrom, dateTo, receiptStatusCode: "02",
    clientTypeCode: "01", pageSize: "200", pageIndex: "1", …}
   -> {"version": "2.0", "total": N, "list": [ … ]}

2) GET  /api/1.0.0/policy/document/BO_{receiptId}
   -> documentData.documentContent  = o PDF em Base64
```

📊 `receiptId` = `{apólice}_{endosso}_{parcela}`, e o documento é `BO_` + ele.
**Sem passo intermediário** — por isso baixar o boleto da MAPFRE é leitura.

📊 **O CPF/CNPJ já vem na primeira chamada**, em
`client.naturalPerson.identityDocumentNumber` (ou `client.legalPerson…` para
empresa). Mais simples que a Yelum, que precisava de uma terceira chamada.

📊 `client.mainPhone` e `client.email` vêm **vazios**. O WhatsApp continua
saindo da gestão (InfoCap), como nas outras quatro.

## 3.1 Os campos obrigatórios que ninguém adivinharia

| Campo | Se vier vazio |
|---|---|
| `brokerId` | 🔴 **HTTP 500** |
| `clientTypeCode` | 🔴 **HTTP 400** `Internal error in the service` |

📊 E `clientTypeCode` **não filtra**: `01` e `02` devolvem o mesmo `total=59`.
Mandamos `01` (o que o app manda) e lemos os dois tipos de pessoa na resposta.

## 3.2 As tabelas de código

```
receiptStatusCode    ''  Todos · 00 Pago · 01 A vencer · 02 Vencida · 99 Cancelada
```

🔴 **Forma de pagamento — a tela mente por omissão:**

```
no <ion-select> da tela:   1 Cartão de Crédito · 2 Débito em Conta · 4 Boleto
nos DADOS reais:           1 · 2 · 4 · 5      ← o 5 também é DÉBITO EM CONTA
```

> 📊 Uma regra *"retém se for 1 ou 2"* deixaria o **5** passar como se gerasse
> boleto: o download falharia e o item sumiria da fila sem uma linha de aviso.
> **A regra é lista de PERMISSÃO: só o `4` gera boleto.** Tudo o mais é retido
> com o motivo escrito para a atendente.

## 3.3 A janela NÃO tem teto — o limite de 31 dias é da tela

📊 Testado numa sessão, um fator por vez, com controle:

```
30 · 31 · 45 · 60 · 90 · 180 · 365 · 730 dias   ->  todas HTTP 200
```

O portal recusa mais de 31 dias **no formulário**; a API aceita 730. A journey
usa **365 dias numa chamada**.

> 📊 E a janela padrão do portal (**15 dias**) devolvia `total: 0` no MESMO dia
> em que 30 dias devolviam **2 vencidas reais**. Confiar nela seria afirmar
> "carteira em dia" com dívida na tela.

## 3.4 A paginação

📊 `pageSize=200` devolveu as 59 linhas de uma vez, com `total` conferindo.
A journey pagina até somar o `total` declarado; `total` maior que o lido é
`needs_human`, nunca "carteira em dia".

## 3.5 🔴 A testemunha do portal MENTE

📊 `GET /distributor/{did}/desk` (com o **token curto**) devolve:

```json
{"clientsSummary": 61, "renovationsSummary": {"auto": 3, "home": 0},
 "pendingReceiptsSummary": "0"}
```

`pendingReceiptsSummary: "0"` — **no mesmo momento em que a lista trazia 2
vencidas**. O cartão do painel não serve como testemunha independente (ao
contrário da Yelum, onde era a melhor das quatro). A testemunha aqui é o
`total` da própria resposta.

## 3.6 O boleto é regerado a cada pedido

📊 A mesma parcela baixada em 12/08 e em 13/08: **mesmo tamanho, hash
diferente** — os encargos são do dia. Não se espera estabilidade de bytes.

📊 E `documentMetadata.size` **mente**: dizia `67548` para um PDF de `19985`
bytes. A validação é `%PDF` nos primeiros bytes, nunca o campo.

## 3.7 O valor da lista ≠ o valor do boleto

📊 `receiptTotFinalAmn: 294.35` na lista · **R$ 301,28** no PDF emitido.
São coisas diferentes: a parcela e o documento com encargos. **Não se força
igualdade e não se inventa juros.**

---

# 4. AS TRAVAS — 🚫 o que o robô nunca toca

```python
ROTAS_PROIBIDAS = (
    "/actions",                # consulta que antecede reprogramar/trocar forma
    "changepaymentmethod",     # trocar forma de pagamento
    "reschedule",              # reprogramar parcela
    "/receipts/export",        # exportação/e-mail em lote
)
```

🔴 **Reprogramar boleto pode custar R$ 50 ao segurado.** Está impresso no
próprio boleto: *"poderão ser cobrados até R$ 50,00 a título de despesa
operacional"*. O robô nunca toca — mas a equipe humana precisa saber.

📊 `POST /distributor/{did}/receipts/{n}/actions` é só leitura de capacidades
(`allowChangePaymentMethod`, `allowReschedule`, `hasHistory` — todos `N` no
caso medido), mas é a **porta de entrada** das duas ações, então fica de fora
junto com elas. A journey não precisa dele: a decisão de reter sai da forma de
pagamento.

> O guarda é **comportamental**, não textual: o teste chama `_api()` com cada
> rota proibida e prova que ela é recusada **antes de sair** — e que uma rota
> permitida sai. Procurar a palavra no arquivo não serviria: `isRescheduled` é
> campo obrigatório do corpo da busca.

---

# 5. OS SERVIÇOS — o mapa para os produtos que vêm depois

📊 Endpoints observados numa sessão real. **Nada aqui foi exercitado pela
cobrança** — é o inventário para Renovação, Cotação, Sinistro e Carteira não
precisarem de outra visita de descoberta.

## 5.1 COBRANÇA 🟢 pronta — `portal_worker/journeys/mapfre_corretor.py`

Ver §3. Journey `mapfre_corretor.cobranca_sweep`, no mapa `JOURNEYS`.

## 5.2 RENOVAÇÃO 🟡 o portal já conta para nós

```
GET /distributor/{did}/desk?brokerId=&productionKey=&isMobile=false
                           &dateTo=dd/mm/aaaa&dateFrom=dd/mm/aaaa   [token CURTO]
 -> renovationsSummary: {"auto": 3, "home": 0}
```

📊 O painel entrega a contagem de renovações por ramo **de graça**, como na
Tokio e na Yelum. ❓ A tela/lista de renovações em si não foi aberta.

## 5.3 CARTEIRA E CLIENTE 360

```
GET /client/{documento}_1/policies        apólices do cliente
GET /client/{documento}_1/tasks           tarefas abertas
GET /client/{documento}_1/interactions    histórico de contato
GET /policy/{policyId}/auto               detalhe da apólice de auto
    policyId = 31_{produtoCod}_{apólice}_{endosso}_TWM
```

📊 `clientsSummary: 61` no `/desk`. O `clientId` é `{CPF/CNPJ}_1`.

## 5.4 PRODUÇÃO, PRODUTOS E COMISSÃO

```
GET  /distributor/{did}/broker/{brokerId}/productionKeys   códigos internos
GET  /distributor/{did}/bonuses?view=00&brokerId=          bônus/campanha
GET  /broker/brokerproducts?brokerId=&productionKey=&agreementCode=   [CURTO]
GET  /broker/{brokerId}/segment?view=00                    segmentação  [CURTO]
GET  /broker/{brokerId}/terms                              termos aceitos
POST /broker/{brokerId}/totalSales?productionKey=&dateTo=&dateFrom=
```

## 5.5 PROPOSTAS E SINISTRO

```
POST /distributor/{did}/proposals            propostas para atuar
POST /distributor/{did}/claims?cacheAge=…    sinistros
GET  /distributor/{did}/branchesclaim        ramos de sinistro
GET  /branchesTypes                          tabela de ramos
```

## 5.6 SESSÃO E INFRAESTRUTURA

```
POST /login                                  autentica
GET  /distributor/{did}/brokers              🔴 as corretoras do login
POST /distributor/{did}/brokerCode           fixa a corretora (o botão Salvar)
GET  /distributor/{did}                      perfil do distribuidor
GET  /distributor/{did}/photo                foto
GET  /banners                                banners do home     [CURTO]
POST /analytics                              telemetria própria
```

❓ **`GET /config/page?path=…`** — é o catálogo de páginas do portal (o
equivalente MAPFRE dos 338 destinos da Tokio), com `url`, `name` e
`codigo_permiso` (ex.: `MANAGE_RECEIPTS`). 📊 Devolve **HTTP 504 com os dois
tokens** quando chamado por `fetch` de dentro da página, embora o app o consuma
normalmente. Fica para a SPEC de Renovação medir.

---

# 6. O QUE A COBRANÇA LÊ E NÃO USA

`policyId` · `businessLine` · `productCode`/`productDesc` · `endorsementId` ·
`client.category` · `brokerProductionKey.productionsKeys`.

Ficam gravados no item porque a Renovação e a Consulta 360 vão precisar deles,
e recolher agora custa zero.

---

# 7. O GATE — o que foi exercitado, e como

📊 **13/08/2026**, journey real contra o portal real, gravando no bucket real
`portal-evidence`:

```
MAPFRE · AutoFleet         done em 129s
  corretora escolhida ..... AUTO FLEET R CORRETORA DE SEGU  (brokerId 55744776)
  ofertadas no modal ...... RESULTA e AUTO FLEET   <- as duas, e escolheu certo
  token ................... 7.049 chars (vistos: 1481, 4710, 7049)
  janela .................. 13/08/2025 a 13/08/2026
  declarado 2 · lidos 2 ... 1 página
  inadimplentes ........... 2
  boletos ................. 2 de 2

LINHA DE CONTROLE
Allianz · AutoFleet        done
  inadimplentes ........... 10
  boletos ................. 10 de 10
```

📊 **A prova não é o que o código disse.** Os 12 arquivos foram **baixados de
volta do bucket** e conferidos: todos começam com `%PDF`.

```
mapfre_corretor/…/boleto-{apólice}_0_8.pdf       19985 bytes  %PDF
mapfre_corretor/…/boleto-{apólice}_0_9.pdf       19991 bytes  %PDF
allianz_corretor/…  10 arquivos                  103–118 KB   %PDF
```

> A linha de controle importa porque esta SPEC tocou `worker.py` e
> `journeys/__init__.py`, que **toda** journey usa. Sem a Allianz repetindo o
> resultado, um sucesso da MAPFRE poderia ser mérito de outra mudança
> (CLAUDE.md §9.2).

📊 **Testes offline:** `backend/tests/test_mapfre_cobranca.py` — **92 asserções
verdes**, contra fixture anonimizada, sem tocar no portal.

---

# 8. O QUE FALTA

| # | O que | De quem |
|---|---|:--:|
| **P-148** | A credencial da Resulta na MAPFRE é **inválida** ("Autenticação inválida!"). Uma tentativa, e parei. | 🧑 Founder/Saionara |
| **P-149** | O deploy do portal-worker com a journey nova — sem ele a MAPFRE não roda pela fila de produção. | 🧑 Founder |
| P-150 | `/config/page` devolve 504 por `fetch`; o catálogo de páginas fica sem mapear. | 🤖 SPEC de Renovação |
| P-151 | A coluna de juros/multa da linha vencida não foi exercitada — o PDF traz o valor com encargos, a lista traz o da parcela. | 🤖 quando houver caso |

---

# 9. HISTÓRICO

| Data | O que |
|---|---|
| 12/08/2026 | Credenciais das duas corretoras gravadas, URL no catálogo, porta **pública** medida. Achado inicial: o modal lista as duas corretoras — risco cross-tenant levantado como hipótese de mecanismo. Carteira "sem inadimplente" na janela padrão de 15 dias. |
| 13/08/2026 | **Sessão real.** O risco cross-tenant deixou de ser hipótese: 59 parcelas de uma corretora e 8 da outra, zero clientes em comum, trocando um campo. Descoberto `/distributor/{did}/brokers` — o guarda virou dado. Corrigido: a janela de 15 dias **escondia 2 vencidas reais**; a API não tem teto de janela; o painel de pendências **mente**; existe a forma de pagamento `5` fora do dropdown; são três tokens e vale o mais novo; o modal de privacidade intercepta o clique; o Ionic exige digitação real. Journey escrita, 92 testes verdes, gate com 2/2 boletos no bucket e Allianz 10/10 como controle. |
