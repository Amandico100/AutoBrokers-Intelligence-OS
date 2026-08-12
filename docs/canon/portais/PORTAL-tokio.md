# PORTAL TOKIO MARINE — Portal Parceiros — o mapa do território

> Um arquivo por seguradora. Serve **cobrança, renovação e cotação** — as seções
> 1 a 4 e a 6 valem para os três; a 5 separa o que já roda do que só está anotado.
>
> **Leia a [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md) antes de mexer
> aqui.** Ela define o método das 5 fases e o teto de visitas. Este arquivo é o
> mapa do território — não substitui a SPEC.
>
> Estado: ✅ **FECHADA** — as 5 fases. Rodou pela fila de produção, `done`, com
> 3 boletos no bucket · 78 asserções verdes
> Última medição: 12/08/2026 · corretor 67828 (AutoFleet)

| Marca | Significado |
|---|---|
| 📊 | medido — li no HAR, no HTML ou na tela, com data |
| ❓ | **não medido** — precisa de captura antes de virar código |
| 🔴 | trava séria |
| 🚫 | o robô nunca toca |

---

# 1. A PORTA

**URL:** `https://portalparceiros.tokiomarine.com.br/`
📊 Confere com o seed em `20260706_05_spec020_portals_seed_insurers.sql:23`.

## 1.1 O login tem UM passo a mais que todos os outros

📊 Depois de usuário + senha **não** cai no portal. Cai numa tela intermediária:

```
        Bem-vindo, RAFAEL DA
   Acesse os Portais da Tokio Marine

        ┌───────────────┐
        │   👤 Corretor │   ← precisa CLICAR
        └───────────────┘
             Sair
```

**É um seletor de portais**, não um aviso. Um card hoje (`Corretor`), mas a tela
existe porque a Tokio publica mais de um portal na mesma conta.

> 🔴 Um robô que assume *"logou = estou dentro"* fica parado nessa tela para
> sempre — e o sintoma é **"a varredura não achou ninguém"**, que é
> indistinguível de carteira em dia. Por isso o `login_check` só devolve `done`
> depois de ver o menu do portal, nunca depois de ver o nome do usuário.

## 1.2 O corretor tem CÓDIGO — e pode ter mais de um

📊 No topo: `CÓDIGO/CORRETOR — 67828 - AUTO FLEET R CORRETORA…` com um `[⇄]`.
📊 O modal `Selecione o seu corretor` abre com busca por nome, código ou CNPJ.
Para a AutoFleet: **`Mostrando de 1 até 1 de 1 registros`** — um código só.

📊 E o HTML da página diz por que:

```js
const isBloqueiaTrocaDeParceiro = eval(true);
const permiteSelecaoParceiro    = eval(false);
```

> 🔴 **Mas a tela existe.** Uma corretora com dois códigos vê **um de cada vez**,
> e o relatório é o do código selecionado. Varrer só o default deixaria metade
> da carteira invisível **em silêncio** — a falha que a SPEC-070 §2 proíbe.
>
> A journey resolve o código pelo próprio portal (`buscarUsuario → codigoInterno`),
> nunca por constante. ❓ Falta medir uma corretora com 2+ códigos — quando
> aparecer, o `corretores: []` do relatório aceita lista, então é enumerar.

## 1.3 Por baixo é Liferay — mas o que interessa é um BFF

📊 A URL é `/group/portal-corretor#item_3` (convenção Liferay). **Porém** as
telas de cobrança não são portlets: são aplicações que falam com um
**BFF em JSON**, com GraphQL de um lado e REST do outro. Ver §5.1.

## 1.4 🔴 Akamai também aqui

📊 O HAR mostra o sensor do **Akamai Bot Manager**, com o caminho ofuscado que
ele usa para não ser reconhecido por nome:

```
GET  /urfection-Murthee-through-fearers-to-you-had-suc          778 KB de JS
POST /urfection-Murthee-through-fearers-to-you-had-suc?d=portalparceiros…
```

Mesma trava da HDI. O conserto já está no worker e vale para as duas:
`--headless=new` (impressão digital em JS) **+ User-Agent limpo** (o cabeçalho).
Detalhe do diagnóstico em [PORTAL-hdi.md §1.4](PORTAL-hdi.md).

## 1.5 🔴 Teto de visitas — o mais baixo que já medi

📊 Em 09/08/2026 o SSO travou depois de **~4 entradas em 30 minutos**. A HDI
aguentou ~15. Por isso a captura desta seguradora saiu **de uma sessão só**, e
toda leitura repetida vem de fixture.

## 1.6 Sem CAPTCHA visível · cookie banner atrapalha

📊 Nenhuma tela mostrou CAPTCHA. ❓ Não descarto depois de N logins.
📊 A tarja de cookies fica **sobre** o conteúdo e intercepta cliques na região
de baixo — fechar (`#agreed-cookie`) é o primeiro ato depois de entrar.

---

# 2. A TOPOLOGIA

## 2.1 Os caminhos até os inadimplentes

📊 **Dois caminhos, mesmo destino:**

```
A) menu FINANCEIRO → coluna "Relatórios Clientes" → Clientes inadimplentes
B) atalho no home  → card "PARCELAS INADIMPLENTES"
```

📊 O menu FINANCEIRO inteiro, com as URLs reais (do JSON de menu do portal):

| Conta Corrente | Relatórios Corretor | Consultas e Pagamentos | **Relatórios Clientes** |
|---|---|---|---|
| Migrar Modelo 🚫 | Acompanhar Emissões | Visão Geral do Cliente | **Clientes inadimplentes** ⬅ |
| Consulta Saldo/Extrato | Relatório Ganhe Mais | Faturamento em Lote | Cobranças no Cartão de Crédito |
| Transferir 🚫 | Extrato Comissão | Declaração Anual de Débitos | Débitos Pendentes |
| Recuperar 🚫 | | Restituições Pendentes | Débitos Não Autorizados |
| Listar Campanhas | | | |

📊 Endereços dos três relatórios que **não** usamos ainda:

```
/portais/api/v1/debitos-pendentes/pendentes
/portais/api/v1/debitos-pendentes/naoAutorizados
/portais/api/v1/power-bi/relatorio/<guid>/<guid>     (cartão de crédito)
```

> ⚠️ **`Clientes inadimplentes` pode não ser a única fonte.** ❓ Falta medir se
> um inadimplente de cartão aparece nela ou **só** nas outras. Se for "só",
> varrer uma tela deixa gente de fora. Está em [PENDENCIAS](../PENDENCIAS.md).

## 2.2 A ponte entre a lista e a apólice

📊 A URL do detalhe, lida do `Referer` real do HAR:

```
/portais/visao-cliente-corretor/detalhe/apolice/00861449959/75111063?cdpn=null
                                               └── CPF ──┘ └ idePol ┘
```

**As duas peças vêm do relatório**: `cpfCnpjCliente` (sem pontuação, com os
zeros à esquerda) e `idePol`. Ou seja — **não é preciso clicar na lupa**. A
ponte é aritmética, e está em `url_detalhe()`.

📊 O próprio portal confirma o padrão:

```json
GET /portais/bff/v1/clientes/integracao/sistemas
{"urlConsultaVisao": "…/portais/visao-cliente-corretor/detalhe/apolice/",
 "urlConsultaVisaoCorporate": "…/detalhe/apolice/detalhesCorporate/"}
```

❓ `detalhesCorporate` é outro caminho, para produtos PJ. Não medido.

---

# 3. AS ARMADILHAS

## 3.1 🔴 O telefone do portal não serve — e as duas telas se contradizem

**A mais perigosa, e a mais fácil de não perceber.** 📊 O mesmo segurado, nas
duas fontes, no mesmo dia:

```
relatório (XML)     numeroTelefone1 = 99381576    numeroTelefone3 = 991314388
tela de detalhe     Tel. Fixo       = 99381576    Tel. Celular    = 999381576
```

`999381576` é literalmente **`9` + o fixo** — a tela *calcula* o celular
prefixando um 9. E `991314388` é **outro número**. Para o mesmo cliente, as duas
telas discordam.

> 🔴 **Regra:** nenhum dos dois vira destinatário. A journey entrega o
> `cpf_cnpj`, e o WhatsApp sai do **sistema de gestão da corretora** (InfoCap,
> Quiver) — que é de onde as atendentes já tiram hoje. Os telefones do portal
> ficam num campo chamado `telefones_portal`, só como pista para a tarefa
> humana. O teste [7] prova que nenhum item sai com a chave `whatsapp`.

## 3.2 🔴 DÉBITO: gerar boleto QUEIMA a única troca da vigência

📊 Texto literal do modal:

> *"Se você está solicitando o boleto para uma apólice com forma de pagamento
> débito em conta / cartão. Esta alteração é **permitida somente uma vez durante
> a vigência do seguro**. Se desejar alterar as demais parcelas para boleto,
> deverá ser realizado o **endosso** de alteração da forma de pagamento."*

Clicar ali (1) muda a forma de pagamento da parcela, (2) **consome** o direito
de fazer isso e (3) é irreversível sem endosso. Ação transacional — SPEC-033
manda parar antes de finalizar.

> 🚫 **O robô nunca gera boleto em DÉBITO ou CARTÃO.** Vai para tarefa humana.

## 3.3 🔴 `Repique = S` segura o envio — decisão de negócio, não técnica

📊 A coluna `repique` (S/N). Na linha de DÉBITO com motivo
`DEBITO NAO EFETUADO - INSUFICIENCIA DE FUNDOS`, `repique = S`.

📊 **Confirmado pelo Founder com as atendentes da AutoFleet (12/08/2026):**

> *As atendentes aguardam todas as tentativas de débito se esgotarem — na Tokio
> e em qualquer outra seguradora. Só depois disso mandam boleto.*

Cobrar hoje quem será debitado amanhã é constranger o segurado por um problema
que talvez já não exista. `repique = S` → **retido**, com o motivo escrito.

## 3.4 🔴 `Pendente` NÃO quer dizer atrasada

📊 O caso que produziu a regra: uma segurada tinha as parcelas **3 e 4** com
situação `Pendente` em 12/08/2026 — a 3 vencia em 10/08 (atrasada há 2 dias) e a
4 em 10/09 (a vencer daqui a um mês).

E foi exatamente aí que **o boleto saiu da parcela errada**: o clique manual
pegou a parcela 4. Pegar "a primeira pendente" acerta às vezes; "a última",
também às vezes. Só o **número que veio do relatório** acerta sempre.
`escolher_parcela()` casa pelo número, e o teste [2] usa as duas.

## 3.5 🟠 O botão vem com as aspas em ENTIDADE HTML

📊 Dentro do atributo `onclick`, as aspas simples chegam como `&#39;`:

```html
onclick="VisaoUnicaClienteJS.carregarVencimentoPermitidoBoleto(
         &#39;7231787615&#39;,&#39;3&#39;,&#39;null&#39;,…)"
```

Um padrão que só aceita `'` casa **zero linhas** — e o sintoma é *"não achei a
parcela"*, que se parece com carteira em dia. 📊 Custou uma rodada de teste.
`_ASPA` aceita as duas formas.

## 3.6 🟠 O GraphQL devolve número em NOTAÇÃO CIENTÍFICA

📊 A mesma apólice, nas duas saídas do mesmo portal:

```
GraphQL   "idepol": 7.5104431E7      "apolice": 3.6731739E7
XML       <idePol>75104431</idePol>  <cdApoliceTmsr>36731739</cdApoliceTmsr>
```

São números JS (double). Cada `int(float(...))` é um lugar a mais para perder
dígito num identificador. **Por isso a journey lê o XML, não o GraphQL** — e de
quebra o XML traz os totais no mesmo documento (§5.1).

## 3.7 🟠 A lista é um snapshot de ONTEM

📊 `"ATUALIZADO EM 11/08/2026"` no home (print de 12/08) e, na própria tela,
*"Os dados dos clientes inadimplentes são atualizados diariamente."*

**Quem pagou hoje de manhã continua na lista.** A carência de 48 h protege
parcialmente. ❓ Falta medir se `Situação Parcela` no detalhe é tempo real — se
for, ela é o desempate, e a journey já visita essa tela de graça.

## 3.8 🟠 Dois números de "ramo" para a mesma apólice

📊 `cdRamo = 312` no relatório e `Ramo 0531` no detalhe da mesma apólice.
`0531` é o ramo SUSEP de automóvel. ❓ Não sei o que é `312`. Enquanto não
souber, nenhum dos dois decide nada, e nenhum vai para a mensagem do cliente.

## 3.9 🔴 Passado certo tempo, a Tokio PARA de emitir 2ª via

📊 Medido em 12/08/2026, na **mesma apólice, no mesmo instante**:

```
parcela 11 · venceu 17/07 · 26 dias de atraso · Pendente · SEM botão de boleto
parcela 12 · vence  19/08 · a vencer          · Pendente · COM botão
```

E as que deram certo na mesma rodada tinham **2 e 7 dias** de atraso.

> 💭 A causa provável é o prazo que o próprio boleto imprime —
> `NÃO RECEBER APÓS 15 DIAS DO VENCIMENTO`. Um ponto além do limite e outro
> dentro **são compatíveis** com isso, mas não provam: falta um caso entre 15 e
> 26 dias. Por isso o código diz o **fato** (vencida há N dias, sem 2ª via) e
> **não** a hipótese.

**Isso não é defeito — é a seguradora dizendo não.** E são duas ausências muito
diferentes, que um "não achei a parcela" escondia:

| O que acontece | O que significa | Quem resolve |
|---|---|---|
| a linha **existe sem botão** | a Tokio recusa a 2ª via | 🧑 atendente negocia com a seguradora |
| a linha **não existe** | relatório e detalhe discordam | 🤖 é defeito nosso, alguém olha |

`porque_sem_boleto()` separa as duas, e o teste [2] prova que os dois textos
conseguem ser diferentes.

## 3.10 🟠 PIX é bloqueado quando há parcela anterior pendente

📊 Resposta real:

```json
POST /portais/bff/v1/consulta-unica/pix/validar {"numeroTitulo":"…","tipoTitulo":"FIC"}
{"mensagem":"Não é possivel realizar o pagamento. Parcela anterior pendente",
 "codigo_mensagem":5, "permite_pagamento_pix":false}
```

Guardado em fixture. Quando o PIX virar canal de pagamento, a regra já está medida.

---

# 4. AS TRAVAS — 🚫 o que o robô nunca toca

| Onde | O que | Por quê |
|---|---|---|
| Modal de boleto | **Gerar Boleto** em DÉBITO/CARTÃO | queima a única troca da vigência (§3.2) |
| Modal de boleto | data de vencimento fora da lista oferecida | reprogramar é decisão comercial |
| Barra do relatório | botão **EMAIL** | dispara e-mail de verdade para alguém |
| `/corp/conta-corrente-front` | Transferir · Recuperar · Migrar Modelo | mexe em dinheiro da corretora |
| `/EndossoRDService`, `…/endosso/…` | endosso | escreve no contrato |

> O botão **EMAIL** merece destaque: fica **colado** nos de exportar
> (XML/EXCEL/PDF) que nós queremos. Um seletor frouxo acerta o errado e manda
> e-mail. Como a journey chama o endpoint direto, o botão nunca é tocado — e o
> teste [8] prova que nenhuma dessas rotas aparece no código.

---

# 5. OS SERVIÇOS

## 5.1 COBRANÇA 🟢 journey escrita — `portal_worker/journeys/tokio_corretor.py`

### A cadeia inteira, medida

```
1) POST /portais/bff/v1/clientes/graphql      {buscarUsuario}
   → codigoInterno = 67828

2) POST /portais/bff/v1/clientes/graphql      {buscarRamos}
   → os ~280 códigos de ramo que o relatório EXIGE receber

3) POST /portais/bff/v1/clientes/reports/parcelas/xml
   {corretores:["067828"], dataInicio:"01-01-1901", dataFim:"12-08-2026",
    parceiros:[], ramos:[…]}
   → O RELATÓRIO INTEIRO, em XML, com a TESTEMUNHA embutida

4) GET  /portais/visao-cliente-corretor/detalhe/apolice/<doc>/<idePol>?cdpn=null
   → HTML; dele sai o `numeroTitulo` de cada parcela

5) POST /portais/bff/v1/consulta-unica/financeiro/prorrogacao
   {numeroTitulo, numeroParcela}
   → LinhaDigitavel · ValorOriginal · ListaVencimentosProrrogacao[]

6) POST /portais/bff/v1/consulta-unica/financeiro/boleto
   {numeroTitulo, dataNovoVencimento}
   → cUrlCSF = a URL do PDF

7) GET  cUrlCSF   (outro host: portal.tokiomarine.com.br)  → o PDF
```

> 📊 A Tokio é **a mais limpa das três**. Allianz e HDI obrigaram a raspar HTML;
> aqui só o passo 4 é HTML, e mesmo ele por um `data-numerotitulo` estável.

### 🟢 A testemunha vem no mesmo documento

```xml
<quantidadeClientes>5</quantidadeClientes>
<quantidadeParcelas>5</quantidadeParcelas>
<valorPremios>3050.3</valorPremios>
<comissaoNaoRecebida>401.43</comissaoNaoRecebida>
```

**Se o parser ler 4 e o documento disser 5, ele sabe que perdeu um.** Na HDI
isso só deu para aproximar por heurística de bytes; aqui a própria seguradora
entrega a conferência. `_conferir_testemunha()` para a varredura e devolve
`needs_human` — nunca "carteira em dia".

### A questão do boleto COM e SEM juros — respondida

📊 O que a prorrogação devolve, para parcela **ainda a vencer**:

```json
{"DataVencimentoOriginal":"10/09/2026","FlagSucesso":true,
 "LinhaDigitavel":"03399.53465 54100.072310 78760.701017 1 15650000034353",
 "ListaVencimentosProrrogacao":[{"dataComparacao":"2026-09-10",
   "valorJuros":0,"valorMulta":0,"valorTotalProrrogacao":343.53}],
 "ValorOriginal":343.53}
```

📊 Para parcela **já vencida**, a lista traz **só datas futuras** — a data
original, que passou, não é opção.

> 🔴 **Para quem já está em atraso, não existe boleto sem multa e sem juros no
> portal.** O que existe é a data mais próxima, que é a de menor acréscimo. É
> essa que `escolher_vencimento()` pega.
>
> E **nós não recalculamos nada**: multa e juros são o número que a Tokio
> imprime. Reproduzir a fórmula seria criar um segundo motor de cálculo
> financeiro, e errar centavos numa cobrança é pior do que não mandar
> (CLAUDE.md §12.1). O teste [6] prova que nem `0.02` nem `0.116667` aparecem
> no código.

📊 E o boleto impresso diz a regra, para quem precisar conferir:
`MULTA DE 2,00% E JUROS DE 0,116667% AO DIA` · `NÃO RECEBER APÓS 15 DIAS`.

### 💡 A linha digitável vem de graça

📊 `LinhaDigitavel` chega na resposta da prorrogação, e o boleto ainda devolve
`cCodigoBarras` + os quatro blocos separados. Dá para mandar o número junto com
o PDF e o cliente paga pelo app do banco sem abrir anexo. Já é guardado em
`boletos[].linha_digitavel`. ❓ Entrar ou não na mensagem é decisão do Founder.

### O que o relatório entrega — mais que qualquer outro portal nosso

```
idePol · cpfCnpjCliente · nmCliente · cdApoliceTmsr · cdEndosso · cdRamo
· codModuloProduto · codigoNegocio · dtVencimento · dtVigenciaProporcional
· formaPagto · motivo · nroParcela · premioParcela · comissaoParcela
· repique · tipo · tipoApolice · cdCorretor · nomeCorretor · numCert
· numOper · ideFact · linha · dddTelefone1..3 · numTelefone1..3
```

## 5.2 RENOVAÇÃO 📋 conhecimento anotado, sem código

📊 As URLs reais, colhidas do JSON de menu — **de graça, sem visita extra**:

```
/massificados/renovacao/#/relatorio/portal/corretor        Relatório de Renovações
/massificados/renovacao/#/processamentoLote                Processamento Emissão Lote
/massificados/renovacao/#/transferencia/portal/corretor    Transferir Renovações
/massificados/renovacao/#/historico/portal/corretor        Histórico de Transferências
/massificados/renovacao/#/propostaRenovacaoFacilitada      Renovação Facilitada
/ems/corporate/apps/ctpj-relatorio-renovacao/#/pesquisa    Relatório Renovação (PJ)
/sva/view/portal/renovacao/#/                              Painel de Renovação (Vida)
```

📊 E o **home já entrega um painel pronto** — "Apólices A Vencer | Não
Renovadas", com card por segmento (Auto · Residencial e Condomínio ·
Imobiliário · Fiança Locatícia · Produtos PJ) e faixas `HOJE:` e `7 DIAS:`.

> Quando o Auxiliar de Renovação existir, **esse painel e o
> `/massificados/renovacao/#/relatorio` são a fonte** — já segmentados por prazo.

## 5.3 COTAÇÃO 📋 conhecimento anotado, sem código

📊 Os cotadores, por produto:

```
/CotadorAutoService/iniciarCotacao                       Auto individual
/massificados/auto/frota/cotador/porta/iniciarCotacao    Auto frota
/CotadorRDService/iniciarCotacao/Residencial             Residencial
/CotadorRDService/iniciarCotacao/Condominio              Condomínio
/massificados/cotador-imobiliario/iniciarCotacao         Imobiliário
/massificados/CotadorFiancaService/iniciarCotacao        Aluguel/Fiança
/aff/ctv/portal/cotador-vida/vida-individual/cotacao     Vida individual
/ems/corporate/apps/ctpj-*                               PJ (cyber, RC, equip., agro)
/ConsultaCotacoes/#/consultaWeb                          Consultar cotações (comum)
/SSC/home/<n>                                            Solicitação com anexo
```

## 5.4 OUTROS SERVIÇOS mapeados

📊 Sinistro (`/sin/tokio-sinistro-view/#/aviso-sinistro`, aluguel, condomínio,
vida, terceiro, transporte) · Vistoria (`/ems/act/vistoria-previa/#/…`) ·
Assistência 24 h (`autoatendimento.tokiomarine.com.br/portais/ui/assistencia24h`)
· Extrato de comissão · Informe de rendimento · Simples Nacional · Manutenção de
usuários · BrokerTech.

📊 Telefones públicos: Central `0800 31 86546` · SAC `0800 703 9000` ·
Ouvidoria `0800 449 0000` · Disque Fraude `0800 707 6060`.

---

# 6. DADOS DA TELA que a cobrança NÃO usa

**Do relatório:** `codigoNegocio` · `numCert` · `numOper` · `ideFact` · `linha`
· `nroCarga` · `tipo` · `tipoApolice` (📊 todos `ACX`) · `comissaoParcela` ·
`primeiraParcelaPendente` (a Tokio trata a 1ª parcela como categoria própria).

**Do detalhe do cliente:** `Código Cliente` · endereço completo · `E-mail`.

**Do detalhe da apólice:** `Proposta` · `Tipo Endosso` · `Data Emissão` ·
`Início/Fim de Vigência` · `Prazo` · `Tipo de Apólice` · `Qtde. Itens` ·
`Segmento` · `Descrição Produto` · **`Apólice Anterior` + `Dt. Ini./Fim Vig.
Apólice Anterior`** — 📊 preenchidos numa das apólices medidas. Isso é
**história de renovação**, e o Auxiliar de Renovação vai querer.

**Do bloco de pagamento:** `Forma de Pagamento` · `Banco` (📊 `000033` =
Santander, o banco do boleto) · `Agência` · `Conta Corrente`.

**Do bloco de parcelas:** `Nº Título` · `Situação` · `Data Pagamento` ·
`Tipo Pagamento` · a coluna **PIX** com QR.

> 📊 Um detalhe que só a lista completa mostra: num dos segurados, as parcelas
> 1, 2 e 3 foram **todas pagas com atraso**. Um Auxiliar de Retenção saberia o
> que fazer com isso. A cobrança, hoje, não usa.

---

# 6bis. AS FASES 4 e 5 — o que a realidade ensinou

📊 12/08/2026, corretora AutoFleet, cadeia inteira contra o portal de verdade:

```
relatorio ................ HTTP 200 · 6.857 bytes · corretor 067828
totais (a testemunha) .... 5 clientes · 5 parcelas · R$ 3.050,30
                           comissao nao recebida R$ 401,43
parcelas lidas ........... 5          ← bate com a testemunha
inadimplentes ............ 5
retidos p/ humano ........ 1          ← o DEBITO com repique = S
detalhe .................. recibo 36713188-4 · HTTP 200 · 4 linhas · achou a parcela
BOLETO ................... ok · 119.259 bytes
```

📊 Os totais batem **exatamente** com o print que o Founder tirou da tela:
`Clientes inadimplentes: 5 · Valor Total de Prêmios: R$ 3.050,30 ·
Comissão não recebida: R$ 401,43`. Duas fontes independentes, mesmo número.

## 📊 Fase 5 — a fila de produção, 12/08/2026 18:53 (23 segundos)

```
job bc1dfaa0 ......... done · 1 tentativa
navegador ............ --headless=new · UA limpo · saida DIRETA (sem proxy)
corretor ............. 67828 AUTO FLEET (veio do BFF, nao de constante)
ramos ................ 285 lidos do portal
relatorio ............ 200 · 6.857 bytes
testemunha ........... 5 clientes · 5 parcelas · R$ 3.050,30 · comissao R$ 401,43
parcelas lidas ....... 5        ← bate
BOLETOS .............. 3 no bucket (119.259 · 131.360 · 119.322 bytes)
retidos p/ humano .... 2
```

📊 Os totais batem **exatamente** com o print que o Founder tirou da tela. Duas
fontes independentes, mesmo número.

**Os 5, um por um** — nada some, cada um com desfecho escrito:

| Parcela | Atraso | Forma | Desfecho |
|---|---|---|---|
| `36713188-4` | 2 d | FICHA | ✅ boleto · multa 23,84 · juros 2,78 · total 1.218,51 |
| `36657978-8` | 7 d | FICHA | ✅ boleto · sem acréscimo |
| `36731942-3` | 2 d | FICHA | ✅ boleto · multa 6,86 · juros 0,80 |
| `36731739-3` | 2 d | **DÉBITO** | 🧑 retido — repique `S`, aguardar esgotar |
| `33599379-11` | 26 d | FICHA | 🧑 retido — a Tokio não emite mais 2ª via (§3.9) |

## O que a Fase 4 ensinou — duas coisas que os testes não pegavam

**1. O formulário de login não existe quando a página carrega.**
📊 `portalparceiros` redireciona para um **SSO ForgeRock OpenAM**:
`ssoportais3.tokiomarine.com.br/openam/XUI/?realm=TOKIOLFR`. Os campos são
`#idToken1` / `#idToken2` / `#loginButton_0`, montados por JS **depois** do
`domcontentloaded`. Preencher logo em seguida acha zero campos — e o worker
devolve *"campos de login nao encontrados"*, como se a credencial fosse o
problema. Espera-se o **campo**, nunca o relógio.

**2. 🔴 O guarda de "estou dentro" foi enganado pela própria porta.**
A primeira versão procurava `a[href*='/group/portal-corretor']` — e **o card
"Corretor" do seletor é exatamente um link para essa URL**. O guarda passou na
tela errada, a varredura seguiu achando que estava dentro, e o BFF devolveu
vazio. Um marco de chegada não pode ser algo que a porta também tem
(CLAUDE.md §9.3). As marcas boas estão em `MARCAS_DE_DENTRO`.

---

# 7. O QUE FALTA

| # | O que | Quem destrava |
|---|---|---|
| 1 | O caso **CNPJ** na URL do detalhe (só CPF foi exercitado até agora) | 🤖 sai na próxima rodada |
| 2 | Onde exatamente fica o limite da 2ª via (entre 15 e 26 dias) — §3.9 | 🤖 aparece sozinho |
| 3 | Se inadimplente de **cartão** aparece na lista principal ou só em `Débitos Pendentes` | 🤖 1 visita |
| 4 | Se `Situação Parcela` do detalhe é **tempo real** (desempate do snapshot D-1) | 🤖 1 visita |
| 5 | Uma corretora com **2+ códigos** de corretor | 🧑 Founder indicar |
| 6 | O que é o ramo **`312`** vs `0531` | 🧑 Founder / atendentes |
| 7 | Se o relatório **pagina** quando há centenas de inadimplentes | 🤖 aparece sozinho |

---

# 8. HISTÓRICO

| Data | O que |
|---|---|
| 09/08/2026 | Reconhecimento inicial. 📊 SSO trava depois de ~4 entradas em 30 min. |
| 12/08/2026 | Credenciais novas gravadas cifradas. **Fases 1–4 fechadas com o HAR do Founder:** BFF GraphQL + REST descoberto, cadeia de 7 passos medida com corpos reais, journey escrita, 70 asserções verdes, e a **visita real trouxe boleto de 119.259 bytes** com os totais batendo com a tela (§6bis). 🔴 Achados: o telefone do portal se contradiz entre duas telas · DÉBITO queima a troca da vigência · `Pendente` ≠ atrasada (o boleto saiu da parcela errada na captura) · aspas em entidade HTML · notação científica no GraphQL · Akamai também aqui. |
