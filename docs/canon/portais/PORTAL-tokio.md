# PORTAL TOKIO MARINE — Portal Parceiros — o mapa do território

> Um arquivo por seguradora. Serve **cobrança, renovação e cotação** — as seções
> 1 a 4 e a 6 valem para os três; a 5 separa o que já roda do que só está anotado.
>
> **Leia a [SPEC-070](../specs/SPEC-070-cobranca-multi-seguradora.md) antes de mexer
> aqui.** Ela define o método das 5 fases e o teto de visitas. Este arquivo é o
> resultado da Fase 1 (reconhecimento) — não substitui a SPEC.
>
> Estado: 🟡 **FASE 1 EM ANDAMENTO** · sem código · reconhecimento por prints
> Última medição: 12/08/2026 · corretor 67828 (AutoFleet)

| Marca | Significado |
|---|---|
| 📊 | medido — li na tela ou no print, com data |
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

**Isso é um seletor de portais**, não um aviso. Um único card hoje (`Corretor`),
mas a tela existe porque a Tokio publica mais de um portal na mesma conta. O robô
que assume "logou = estou dentro" fica parado nessa tela para sempre.

> 🔴 **Regra:** o `login_check` da Tokio só devolve `ok` depois de atravessar o
> seletor e ver o menu `FINANCEIRO` na tela. Ver o nome "Bem-vindo" **não** prova
> que entrou.

## 1.2 O corretor tem CÓDIGO — e pode ter mais de um

📊 No topo do portal:

```
CÓDIGO/CORRETOR
67828 - AUTO FLEET R CORRETORA …   [⇄]
```

O `[⇄]` é um **trocador**. Uma corretora com dois códigos vê **um de cada vez** —
e a lista de inadimplentes é a do código selecionado.

> 🔴 **Consequência direta:** varrer só o código default pode deixar metade da
> carteira invisível, e **em silêncio**. É exatamente a falha que a SPEC-070 §2
> proíbe. A varredura tem de enumerar os códigos e rodar um por um.

❓ Falta medir: quantos códigos cada corretora tem, e como o portal expõe a lista.

## 1.3 Liferay por baixo

📊 A URL é `portalparceiros.tokiomarine.com.br/group/portal-corretor#item_3`.
`/group/<site>` é a convenção do **Liferay**. Isso importa: as telas internas são
*portlets*, endereçadas por `p_p_id` / `p_p_lifecycle` / `_<portlet>_<param>`.
A cadeia de chamadas in-page da SPEC-033 se aplica; o formato dos parâmetros é o
do Liferay, não um REST limpo.

## 1.4 🔴 Teto de visitas — medido e severo

📊 Em 09/08/2026, no reconhecimento inicial, o SSO da Tokio **travou depois de
~4 entradas em 30 minutos**. É o teto mais baixo dos portais que já visitei
(a HDI aguentou ~15).

> Por isso a captura desta seguradora precisa sair **de uma sessão só**. Cada
> tentativa desperdiçada custa meia hora de espera.

## 1.5 Sem CAPTCHA visível

📊 Nenhum dos prints mostra CAPTCHA. ❓ Não descarto — a trava pode aparecer só
depois de N logins seguidos, como na Porto.

## 1.6 Cookie banner

📊 A tarja de cookies cobre a parte de baixo da tela e **fica sobre o conteúdo**
("ENTENDI · SAIBA MAIS · ✕"). Num navegador automatizado ela intercepta cliques
na região inferior. Fechar é o primeiro ato depois de entrar.

---

# 2. A TOPOLOGIA

## 2.1 Os caminhos até os inadimplentes

📊 **Dois caminhos, mesmo destino:**

```
A) menu FINANCEIRO → coluna "Relatórios Clientes" → Clientes inadimplentes
B) atalho no home  → card "PARCELAS INADIMPLENTES"
```

📊 O menu FINANCEIRO inteiro, medido no print de 12/08/2026:

| Conta Corrente | Relatórios Corretor | Consultas e Pagamentos Clientes | **Relatórios Clientes** | Materiais |
|---|---|---|---|---|
| Migrar Modelo | Acompanhar Emissões | Visão Geral do Cliente | **Clientes inadimplentes** ⬅ | Vídeos |
| Consulta Saldo/Extrato | Relatório Ganhe Mais | Faturamento em Lote | Cobranças no Cartão de Crédito | Informativos e Tutoriais |
| Transferir | Extrato Comissão *(novo)* | Faturamento em Lote *(novo)* | Débitos Pendentes | |
| Recuperar | | Declaração Anual de Débitos | Débitos Não Autorizados | |
| Listar Campanhas | | Restituições Pendentes | | |

> ⚠️ **`Clientes inadimplentes` não é a única fonte.** Existem ainda
> `Débitos Pendentes`, `Débitos Não Autorizados` e `Cobranças no Cartão de Crédito`.
> ❓ Falta medir se um inadimplente de cartão aparece na lista principal ou **só**
> nessas outras telas. Se for "só", varrer uma tela só deixa gente de fora — o
> pecado capital da SPEC-070.

## 2.2 A cadeia da cobrança, tela a tela

```
login → seletor "Corretor" → home
  → FINANCEIRO ▸ Clientes inadimplentes
      → LISTA (n linhas, já com telefone, forma de pagamento e motivo)
        → lupa 🔍 na linha
          → "Visão Geral – Cliente" / Detalhes da Apólice
            → bloco "Dados Parcela"
              → coluna Ação: ícone 📄 na parcela Pendente
                → modal "Atualizar ou Gerar 2ª Via de Boleto"
                  → linha digitável + botão "Gerar Boleto"
              → coluna PIX: ícone de QR Code
```

---

# 3. AS ARMADILHAS

## 3.1 🔴 O telefone da LISTA é o FIXO — não serve para WhatsApp

**A mais perigosa, e a mais fácil de não perceber.** 📊 Comparando o mesmo
segurado nas duas telas, 12/08/2026:

```
LISTA de inadimplentes    Telefone ......... 48 91002403     ← 8 dígitos
DETALHE do cliente        Tel. Fixo ........ 48 91002403     ← o mesmo
                          Tel. Celular ..... 48 991002403    ← 9 dígitos, ESTE
```

A lista traz **uma** coluna "Telefone" e ela carrega o **fixo**. Mandar WhatsApp
para o número da lista é mandar para um telefone que não recebe WhatsApp — e o
envio some sem erro visível.

> 🔴 **Regra:** o telefone da lista **nunca** vira destinatário. O celular só
> aparece no detalhe da apólice, que já visitamos para pegar o boleto. E mesmo
> ele é fallback: a fonte primária continua sendo o sistema de gestão da
> corretora (decisão do Founder, Q2).

## 3.2 🔴 DÉBITO: gerar boleto QUEIMA a única troca da vigência

📊 Texto literal do modal, 12/08/2026:

> *"Se você está solicitando o boleto para uma apólice com forma de pagamento
> débito em conta / cartão. **Esta alteração é permitida somente uma vez durante
> a vigência do seguro.** Se desejar alterar as demais parcelas para boleto,
> deverá ser realizado o endosso de alteração da forma de pagamento da apólice."*

Isto não é um aviso decorativo. Clicar "Gerar Boleto" numa parcela de **DÉBITO**:

1. muda a forma de pagamento **daquela parcela**;
2. **consome** o direito de fazer isso — uma vez por vigência;
3. e é **irreversível sem endosso**.

> 🚫 **O robô nunca clica "Gerar Boleto" numa linha com Forma Pagamento = DÉBITO
> ou CARTÃO.** Vai para tarefa humana, como já decidido para a HDI.

Isso encaixa exatamente na SPEC-033: *ação transacional → pare antes de finalizar*.

## 3.3 🟠 "Repique = S" pode significar que a cobrança ainda vai ser tentada

📊 A lista tem uma coluna `Repique` (S/N). Na linha de DÉBITO com motivo
`DEBITO NAO EFETUADO - INSUFICIENCIA DE FUNDOS`, `Repique = S`.

Repique, em cobrança, é **nova tentativa de débito**. Se a Tokio vai tentar de
novo sozinha, cobrar o cliente hoje é constranger alguém que talvez já esteja
resolvido amanhã.

❓ **Precisa de confirmação humana** (atendentes da AutoFleet) antes de virar
regra. Se confirmado: `Repique = S` **segura** o envio e vira tarefa humana com
o motivo escrito.

## 3.4 🟠 A lista é um snapshot de ONTEM, não tempo real

📊 Dois lugares dizem a mesma coisa:

```
home ......... "ATUALIZADO EM 11/08/2026"   (print tirado em 12/08)
lista ........ "Os dados dos clientes inadimplentes são atualizados diariamente."
```

**Consequência:** quem pagou hoje de manhã **continua na lista**. A carência de
48 h que já aplicamos protege parcialmente, mas o risco real é cobrar quem já
pagou. ❓ Medir se a tela de detalhe (Dados Parcela → `Situação Parcela`) é
tempo real. Se for, ela é o **desempate**: a lista aponta, o detalhe confirma.

> Regra provável: `lista diz inadimplente` **E** `detalhe diz Pendente` → envia.
> Só a lista → não envia.

## 3.5 🟠 Dois números de "ramo" para a mesma apólice

📊 Mesma apólice 36713188:

```
LISTA .......... Ramo 312
DETALHE ........ título "(312 / 36713188)"  mas  Dados Básicos → Ramo 0531
```

`0531` é o ramo SUSEP de automóvel; `312` é outra coisa (código comercial?).
❓ Não sei qual é qual. Enquanto não souber, **não uso nenhum dos dois** para
decidir nada — e nenhum vai para a mensagem do cliente.

## 3.6 🟠 O modal não abre em página nova

📊 O boleto sai de um **modal sobreposto**, não de um `window.open` como na HDI.
❓ O download em si — se é `window.open`, `<a download>` ou POST que devolve o
PDF — não foi medido.

---

# 4. AS TRAVAS — 🚫 o que o robô nunca toca

| Onde | O que | Por quê |
|---|---|---|
| Modal de boleto | **Gerar Boleto** em linha DÉBITO/CARTÃO | queima a única troca da vigência (§3.2) |
| Modal de boleto | **DATA DO NOVO VENCIMENTO** ≠ a data já selecionada | reprogramar vencimento é decisão comercial |
| FINANCEIRO ▸ Conta Corrente | Transferir · Recuperar · Migrar Modelo | mexe em dinheiro da corretora |
| Lista | botão **EMAIL** | dispara e-mail de verdade para alguém |
| Qualquer tela | endosso, alteração de forma de pagamento | contrato |

> O botão **EMAIL** na barra da lista merece destaque: está a um clique dos
> botões de exportar (XML/EXCEL/PDF) que **queremos** usar. Um seletor frouxo
> acerta o errado e manda e-mail. O seletor precisa ser exato.

---

# 5. OS SERVIÇOS

## 5.1 COBRANÇA 🟡 mapeada, sem código

### O que a LISTA já entrega — e é mais que qualquer outro portal

📊 Colunas medidas em 12/08/2026:

```
Segurado · CPF/CNPJ · Negócio · Ramo · Apólice · Endosso · Vigência Proporcional
· Telefone · Vencimento · Parcela · Valor Parcela · Forma Pagamento · Motivo
· Repique · Origem Venda · Sistema Origem · 2ª Via (🔍)
```

E um cabeçalho de totais:

```
Clientes inadimplentes: 5      Valor Total de Prêmios: R$ 3.050,30
Comissão não recebida: R$ 401,43
1ª Parcela Pendente: 0         Parcelas Pendentes: 5
```

> 📊 **`Total de registros: 5` é a testemunha.** Se o parser ler 4, ele **sabe**
> que perdeu uma. É o guarda contra "carteira em dia" mentiroso que a HDI só
> conseguiu por heurística de bytes. Aqui o portal diz o número. Usar.

### 🟢 A porta boa: EXCEL / XML

📊 A barra da lista tem `EMAIL · XML · EXCEL · PDF`.

Se o XML ou o EXCEL devolver os mesmos registros, a cobrança da Tokio **não
precisa de parser de HTML**. Um arquivo estruturado é mais estável que uma
`<table>` — e imune a mudança de layout.

> **Fase 2 começa por aqui**, não pelo HTML. É a diferença entre um parser que
> quebra a cada redesign e um que não.

### A questão do boleto COM e SEM juros

📊 O que o modal mostra, para a parcela vencida há 2 dias:

```
Data do Vencimento Original ...... 10/08/2026
Dias em Atraso (A) ............... 2
Valor do Documento (B) ........... R$ 1.191,89
Multa (C) ........................ R$ 23,84
Juros (D) ........................ R$ 2,78
Valor Cobrado (B + C + D) ........ R$ 1.218,51

DATA DO NOVO VENCIMENTO: [ 12/08/2026 ▾ ]   → [Gerar Boleto]

linha digitável: 03399.53465 54100.071866 12318.001018 9 1534000011918…
```

📊 E a dica da própria Tokio, literal:

> *"Não há necessidade de gerar 2ª via de boleto para pagamento de parcelas
> vencidas. O cálculo de juros e multa é calculado automaticamente ao efetuar o
> pagamento no seu correspondente bancário ou lotéricas."*

**Leitura:** existem duas coisas diferentes, e as atendentes estão certas.

| | Boleto ORIGINAL | 2ª via REPROGRAMADA |
|---|---|---|
| Valor impresso | o original, **sem** multa e juros | com multa e juros **embutidos** |
| Vencimento | o original, já passado | a data nova escolhida |
| Quem calcula o acréscimo | o **banco**, na hora de pagar | a **Tokio**, na geração |
| Ação nossa | ler | **escrever** — muda a data |

> 🔴 **Nós não recalculamos juros.** Nunca. Multa e juros são o número que a
> Tokio imprime; reproduzir a fórmula é criar um segundo motor de cálculo
> financeiro — e errar por centavos em cobrança é pior que não mandar.

❓ **A decisão que falta** (precisa do Founder): mandar ao segurado o boleto
original, a 2ª via reprogramada, ou os dois? A recomendação técnica é o
**original**, porque é leitura pura e é o que a própria Tokio recomenda.

### 💡 A linha digitável é um ativo que os outros portais não deram

📊 O modal exibe a linha digitável em texto, com botão "Copiar Código do Boleto".
Isso permite mandar no WhatsApp **o número junto com o PDF** — e o cliente paga
pelo app do banco sem abrir anexo.

❓ Falta decidir se entra na mensagem. Tecnicamente é de graça: já está na tela.

### 🟢 PIX

📊 A coluna `PIX` no bloco Dados Parcela tem um ícone de QR Code na parcela
pendente. ❓ Não medido o que ele devolve (imagem? copia-e-cola?). Se devolver
o **copia-e-cola**, é a forma de pagamento com menor atrito que qualquer
seguradora nossa oferece hoje.

## 5.2 RENOVAÇÃO 📋 conhecimento anotado, sem código

📊 Achado de graça no reconhecimento:

**Menu `RENOVAÇÕES`** existe no topo (❓ submenus não medidos).

**E o home já entrega um painel pronto** — "Apólices A Vencer | Não Renovadas",
com um card por segmento e uma faixa de prazo:

```
Auto  ·  Residencial e…  ·  Imobiliário  ·  Fiança  ·  Produtos PJ
                     … · HOJE: … · 7 DIAS: …
```

> Quando o Auxiliar de Renovação existir, **este painel é a fonte** — está no
> home, não exige navegação, e já vem segmentado por prazo. Vale mais que
> qualquer relatório que a gente montasse.

Também no home: `PRÊMIO EMITIDO` por mês e `MEU GERENTE`.

## 5.3 COTAÇÃO 📋 conhecimento anotado, sem código

📊 Menus do topo: `PRODUTOS` · `CONSULTAS` · `BROKERTECH`.
📊 Card do home: `PROPOSTAS PENDENTES PARA EMISSÃO` e `PROPOSTAS CONTRATADAS`.
📊 Rodapé: `Consultar Cotações` · `Acompanhar Emissão` · `2ª Via Boleto, Apólice e Endosso`.

❓ Nada medido por dentro.

## 5.4 OUTROS SERVIÇOS vistos no rodapé

`Aviso de Sinistro` (Auto · Condomínio · Demais Produtos · Terceiro · Vida) ·
`Acompanhar Sinistro` · `Agendamento de Vistoria` (Segurado e Terceiro) ·
`Condições Gerais` · `Questionários` · `Fale Conosco/SAC`.

📊 Telefones públicos do rodapé: Ouvidoria `0800 449 0000` · Disque Fraude
`0800 707 6060` · Central (do modal) `0800 31 86546`.

---

# 6. DADOS DA TELA que a cobrança NÃO usa

Ficam aqui porque **custaram uma visita** e outro Auxiliar vai querer:

**Da lista:** `Negócio` (nº interno) · `Endosso` · `Vigência Proporcional` ·
`Origem Venda` · `Sistema Origem` (📊 todas as 5 linhas = `ACX`) ·
`Comissão não recebida` · `1ª Parcela Pendente` (separada das demais — a Tokio
trata a primeira parcela como categoria própria).

**Do detalhe do cliente:** `Código Cliente` · endereço completo (logradouro,
número, bairro, cidade, UF, CEP) · `E-mail` · `Tel. Fixo` · `Tel. Celular`.

**Do detalhe da apólice:** `Proposta` · `Tipo Endosso` · `Data Emissão` ·
`Início/Fim de Vigência` · `Prazo` · `Tipo de Apólice` · `Qtde. Itens` ·
`Segmento` · `Descrição Produto` · `Parceiro de Negócio` · `Apólice Anterior`
(📊 vazio aqui — quando preenchido, é **história de renovação**).

**Do bloco de pagamento:** `Forma de Pagamento` · `Banco` (📊 `000033` = Santander)
· `Agência` · `Conta Corrente`.

**Do bloco de parcelas:** `Nº Título` (📊 `7186123180` — é o identificador do
boleto, provavelmente a chave de download) · `Situação Parcela` ·
`Data Pagamento` · `Tipo Pagamento`.

> 📊 Um detalhe que só a lista completa mostra: neste segurado, as parcelas 1, 2
> e 3 foram **todas pagas com atraso** (01/05→04/05, 10/06→15/06, 10/07→17/07).
> Um Auxiliar de Retenção saberia o que fazer com isso. A cobrança, hoje, não usa.

---

# 7. O QUE FALTA — a lista de captura da Fase 1

Ver a mensagem de handoff. Em resumo, tudo que está marcado ❓ acima, mais:

1. a resposta de `XML` e de `EXCEL` na lista de inadimplentes;
2. as chamadas de rede (F12 ▸ Network) da lista, do detalhe e do modal;
3. o HTML da lista e do detalhe (`Ctrl+U` / salvar página);
4. o que o ícone 📄 faz de fato (baixa PDF? abre modal? as duas?);
5. o que o ícone PIX devolve;
6. a lista de códigos de corretor de cada corretora;
7. confirmação humana sobre `Repique = S`.

---

# 8. HISTÓRICO

| Data | O que |
|---|---|
| 09/08/2026 | Reconhecimento inicial. 📊 SSO trava depois de ~4 entradas em 30 min. |
| 12/08/2026 | Credenciais novas de Resulta e AutoFleet gravadas cifradas. Fase 1 por prints: seletor de portais, menu FINANCEIRO completo, lista de inadimplentes, detalhe da apólice, modal de 2ª via. 🔴 Achados: telefone da lista é o fixo · DÉBITO queima a troca da vigência · lista é snapshot D-1 · existe exportação XML/EXCEL. |
