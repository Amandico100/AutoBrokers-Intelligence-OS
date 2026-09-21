# Roteiro de captura — Portal de Vidros

> **Para quem é:** Regina (atendimento) — e o Founder lê junto.
> **Para que serve:** cada acionamento que você faz no portal é a única maneira de
> o robô aprender a fazer aquilo sozinho. Este roteiro diz, tela por tela, o que
> clicar, o que salvar e como nomear.
> **v2.0 · 21/09/2026** · baseado em **cinco** capturas já medidas (Yelum para-brisa
> 20/09 ✅ **nova**, Yelum lataria 09/09, Yelum vidro de porta 15/08, Porto lanterna
> 15/08, Porto roda 15/08).
>
> 🔴 **O que mudou na v2.0:** a captura do **para-brisa** foi feita e respondeu quase
> tudo o que se esperava dela (veja a §3.1). A lista do que ainda falta foi **reescrita
> por ordem de valor** e está na **§5** — a nº 1 vale mais que todas as outras juntas.

---

## Em uma frase

> **Você já faz o acionamento todo dia. A única coisa nova é: abrir o F12 antes
> de começar, salvar cada tela, e no fim exportar um arquivo. Mais nada muda.**

---

## Índice

1. [Preparação do navegador — uma vez por acionamento](#1-preparação-do-navegador--uma-vez-por-acionamento)
2. [O fluxo tela por tela](#2-o-fluxo-tela-por-tela)
3. [O que muda em cada serviço](#3-o-que-muda-em-cada-serviço)
4. [O que muda em cada seguradora](#4-o-que-muda-em-cada-seguradora)
5. [O QUE AINDA FALTA CAPTURAR — em ordem de valor](#5-o-que-ainda-falta-capturar--em-ordem-de-valor-v20--21092026)
6. [O que enviar ao Founder no fim](#6-o-que-enviar-ao-founder-no-fim)
7. [O que NÃO fazer](#7-o-que-não-fazer)

---

## 1. Preparação do navegador — uma vez por acionamento

Serve para Chrome ou Edge (é a mesma tela nos dois).

### 1.1 Antes de tudo: crie a pasta do acionamento

Na sua área de trabalho, crie uma pasta com este nome:

```
SEGURADORA - SERVIÇO - AAAA-MM-DD
```

Exemplos reais:

```
YELUM - PARA-BRISA - 2026-09-15
PORTO - LANTERNA - 2026-09-16
BRADESCO - VIDRO DE PORTA - 2026-09-17
```

**Tudo daquele acionamento vai para dentro dessa pasta.** Um acionamento, uma
pasta. Se você fizer dois no mesmo dia, são duas pastas.

### 1.2 Abrir o "gravador" do navegador (DevTools)

🔴 **Isto tem de ser feito ANTES de clicar em "Iniciar atendimento".** O
gravador só grava o que acontece depois que ele foi aberto. Se você abrir no
meio, perdemos o começo — e o começo é onde o portal decide se a apólice tem
cobertura.

Passo a passo:

1. Abra o portal: `https://abraseuatendimento.com.br`
2. **Antes de clicar em qualquer coisa**, aperte **F12**.
   (Se o F12 não abrir: clique com o botão direito em qualquer lugar branco da
   página → **Inspecionar**.)
3. Vai abrir um painel na lateral ou embaixo. No topo dele há abas:
   *Elements · Console · Sources · **Network** · Performance…*
   👉 **Clique na aba `Network`** (em português pode aparecer como **Rede**).
4. Dentro da aba Network, logo abaixo das abas, há uma linha de opções.
   👉 **Marque a caixinha `Preserve log`** (em português: **Preservar registro**).
   Isso faz o gravador **não apagar** o que gravou quando a página muda de tela.
   Sem isso, cada passo apaga o anterior e no fim só sobra a última tela.
5. A caixinha **`Disable cache`** — **tanto faz**. Deixe como estiver. Ela não
   atrapalha nem ajuda.
6. **Não escreva nada no campo de filtro** (aquela caixinha com uma lupa ou
   escrito `Filter`). Se houver alguma palavra escrita ali, apague. Filtro
   escrito = gravação incompleta.
7. Confira: a bolinha no canto superior esquerdo do painel Network tem de estar
   **vermelha** (gravando). Se estiver cinza, clique nela para ligar.

✅ Pronto. **Agora sim** clique em "Iniciar atendimento" e faça o acionamento
normalmente.

> 💡 O painel ocupa metade da tela e atrapalha um pouco. Você pode arrastar a
> borda dele para deixá-lo mais fino, ou clicar nos três pontinhos `⋮` do painel
> → **Dock side** → escolher embaixo. **Não feche o painel.**

### 1.3 Salvar cada tela como HTML

Em **cada** tela do fluxo (a lista completa está na §2):

1. Clique com o botão direito numa área vazia da página → **Salvar como…**
   (ou aperte **Ctrl + S**).
2. Em "Tipo" / "Salvar como tipo", escolha:
   👉 **`Página da Web, completa`** (em inglês: *Webpage, Complete*).
   🔴 **Não** escolha "Somente HTML" nem "Arquivo único". O "completa" é o que
   traz junto os textos das listas e os desenhos do carro.
3. Salve **dentro da pasta do acionamento**, com o nome da regra da §1.5.

O navegador vai criar, ao lado do `.html`, uma pasta com o mesmo nome terminando
em `_files` ou `_arquivos`. **Deixe ela lá.** Ela faz parte da captura.

### 1.4 Tirar print (foto da tela)

Aperte **Windows + Shift + S**. O mouse vira uma cruz. Arraste selecionando a
área que quer fotografar (ou a tela inteira). A imagem vai para a área de
transferência — abra o **Paint**, cole com **Ctrl + V** e salve como `.png`
dentro da pasta do acionamento.

> 💡 Atalho melhor: depois de apertar Win+Shift+S aparece um aviso no canto
> inferior direito. Clicando nele, abre a ferramenta de recorte já com a imagem —
> e dali dá para salvar direto com **Ctrl + S**.

**O print é obrigatório sempre que houver uma lista/dropdown para abrir** (§2).
O HTML não guarda a lista aberta; o print guarda.

### 1.5 A regra de nome dos arquivos

```
SEGURADORA - SERVIÇO - NN - nome da tela.extensão
```

- `NN` = número de dois dígitos na ordem em que a tela apareceu: `01`, `02`, `03`…
- `nome da tela` = o que você entendeu daquela tela, em palavras simples.

Exemplos:

```
YELUM - PARA-BRISA - 01 - menu da seguradora.html
YELUM - PARA-BRISA - 02 - passo 1 cpf placa data.html
YELUM - PARA-BRISA - 03 - passo 3 peca e causa.html
YELUM - PARA-BRISA - 03 - passo 3 lista de pecas ABERTA.png
YELUM - PARA-BRISA - 04 - questionario 80.html
YELUM - PARA-BRISA - 07 - calendario com dias disponiveis.png
```

🔴 **Os números têm de seguir a ordem real em que você viu as telas.** É por eles
que a gente reconstrói o caminho.

### 1.6 No fim: exportar o HAR (o arquivo mais importante)

🔴 **Faça isto ANTES de fechar a aba.** Se você fechar a aba, o gravador esvazia
e não há como recuperar.

1. Volte ao painel do F12, aba **Network**.
2. Procure o ícone de **seta para baixo** (⬇️) na linha de ícones do topo do
   painel — fica perto da bolinha vermelha e do símbolo 🚫. Passando o mouse,
   aparece o texto **`Export HAR...`**.
   - Se não achar o ícone: clique com o **botão direito** em qualquer linha da
     lista de requisições. No menu que abre, procure
     **`Save all as HAR with content`** (em português: *Salvar tudo como HAR com
     conteúdo*).
   - Em versões novas do Chrome, o botão ⬇️ abre um menuzinho com duas opções.
     👉 Escolha a que diz **`with content`** / **`com conteúdo`**.
3. Salve dentro da pasta do acionamento com o nome:
   ```
   SEGURADORA - SERVIÇO - captura.har
   ```

#### Por que o "**with content**" importa (leia, é rápido)

O portal conversa com o sistema da seguradora por trás da tela. O HAR grava essa
conversa. Existem duas versões:

| opção | o que grava | serve? |
|---|---|---|
| `Export HAR` (sem conteúdo) | **só os endereços** — "pedi a lista de peças" | ❌ não |
| `Save all as HAR **with content**` | os endereços **e as respostas** — "pedi a lista de peças e ela veio com estas 21 peças, estes códigos e estes preços" | ✅ **é esta** |

Sem o conteúdo, o arquivo é uma lista de portas fechadas. Com o conteúdo, é o
manual da seguradora. **É a diferença entre a captura servir e não servir.**

> ⚠️ O arquivo vai ficar grande — de 10 a 30 MB. **Isso é normal e é bom sinal.**
> Um HAR de 200 KB quase certamente foi exportado sem conteúdo.

---

## 2. O fluxo tela por tela

Este é o portal `abraseuatendimento.com.br`, que **38 seguradoras** usam (§4).
O caminho é sempre o mesmo; o que muda é o catálogo de peças de cada apólice.

### 🔴 A REGRA DE OURO

> **Não cancele, não desista e não feche a aba antes da última tela terminar de
> carregar por completo.**

Três motivos, todos medidos:

1. O **número do atendimento nasce no meio do caminho**, não no fim. Depois que
   ele nasce, o pedido já existe na seguradora. Fechar a aba não desfaz — só
   deixa um pedido aberto que ninguém está acompanhando.
2. As telas do fim — agendamento, confirmação, comprovante — são justamente as
   que **nunca conseguimos capturar**. Nas quatro capturas que temos, três foram
   canceladas ou abandonadas antes delas.
3. Quando a tela ainda está carregando, a conversa com a seguradora ainda está
   acontecendo. Fechar no meio corta a gravação pela metade.

Se você **precisar** cancelar (o segurado desistiu, você errou um dado):
👉 **cancele pelo botão do portal, espere a tela de cancelamento aparecer
inteira, salve ela também, e só então exporte o HAR.** Um cancelamento capturado
por inteiro também nos ensina — o que não ensina nada é a aba fechada no meio.

### 2.0 · Tela: **Selecione a seguradora**

- **Endereço:** `abraseuatendimento.com.br/#/`
- **O que fazer:** nada ainda — **abra o F12 primeiro** (§1.2). Depois escolha a
  seguradora do segurado.
- **Capturar:** `NN - 00 - lista de seguradoras.png` — 🔴 **abra o campo de
  seguradora e tire print com a lista inteira aberta**, rolando até o fim se
  precisar (pode precisar de 2 ou 3 prints).
  Isso vale **uma vez só**, na primeira captura que você fizer. Nas seguintes,
  pule.

### 2.1 · Tela: **Menu de atendimento** (`Iniciar` / `Consultar atendimento`)

- **Endereço:** `#/<seguradora>/menu-atendimento`
- **O que aparece:** dois caminhos — **Iniciar atendimento** e
  **Consultar atendimento**.
- **O que fazer:** clique em **Iniciar atendimento**.
- **Capturar:** HTML + print → `01 - menu da seguradora`
- 🔴 **Ponto que nunca capturamos:** o **Consultar atendimento**. Ver a captura
  nº 8 da §5 — é uma captura separada, não misture com esta.

### 2.2 · Tela: **Passo 1 — CPF, placa e data do dano**

- **Endereço:** `#/<seguradora>/passo1`
- **O que preencher:** CPF/CNPJ do titular · placa · data do dano.
- **⚠️ Só na Porto Seguro** aparece a mais, nesta tela:
  **`Selecione a cobertura desejada`** com dois botões —
  `Vidros, faróis/lanternas e retrovisores` · `Roda, pneu e suspensão`.
- **Capturar:** HTML + print → `02 - passo 1 cpf placa data`
  - **Na Porto:** um print a mais, mostrando os dois botões de cobertura.
- **Se der erro aqui** (ex.: *"A apólice do veículo informado não possui cláusula
  de … contratada"*): 🔴 **capture assim mesmo!** HTML + print da mensagem de
  erro, e exporte o HAR. Um acionamento que morre aqui é valiosíssimo — é como o
  robô aprende a avisar "não tem cobertura" **antes** de abrir pedido nenhum.

### 2.3 · Tela (janelinha lateral): **Dados da apólice**

- Abre por cima, mostrando o que a seguradora encontrou: nome, veículo, apólice.
- **O que fazer:** conferir e **Confirmar**.
- **Capturar:** print → `03 - modal dados da apolice`
  ⚠️ Este print tem dados do segurado. Mande mesmo assim — o Founder trata como
  material confidencial e não vai para lugar nenhum além de nós.

### 2.4 · Tela: **Passo 2 — Confirme seus dados (20%)**

- **Endereço:** `#/<seguradora>/passo2/…`
- **O que preencher:** relação com o titular (você escolhe **Corretor**) ·
  e-mail · nome · CPF/CNPJ · telefone · **tipo do telefone** (uma listinha:
  Comercial, Recado, Celular do segurado, Celular do corretor, Residência do
  segurado) · e há uma caixinha **`Quero receber atualizações via WhatsApp`**.
- 🔴 **Decisão já tomada pelo Founder: deixe a caixinha do WhatsApp DESMARCADA.**
  O telefone desta tela é o da corretora, não o do segurado — marcar mandaria os
  avisos da seguradora para o mesmo WhatsApp onde o nosso agente conversa, e
  ninguém saberia quem disse o quê.
- **Capturar:** HTML + print → `04 - passo 2 dados do solicitante`
  - 🔴 **um print a mais com a lista `Tipo de telefone` ABERTA.**

### 2.5 · Tela: **Passo 3 — Nos conte o que aconteceu (50%)**

🔴 **É a tela mais importante de todo o roteiro.** É aqui que se escolhe a peça,
e é a escolha da peça que define tudo o que vem depois.

- **Endereço:** `#/<seguradora>/passo3/…`
- **O que aparece:**
  - **`Qual foi a peça danificada?`** (ou `Peça danificada`) — uma lista.
  - **`Como ocorreu o dano ao veículo?`** (ou `Motivo do dano`) — outra lista,
    que **muda conforme a peça escolhida**.
  - **`Onde ocorreu o dano ao veículo?`** — `Urbano (Cidade)` · `Rodoviário` ·
    `Não sabe`.
  - **`Descreva como aconteceu`** — texto livre, mínimo 30 caracteres.
  - Em alguns casos: **`Mais de um item danificado?`** e
    **`O item permanece no veículo?`**.
- **No serviço de lataria/martelinho** esta tela é diferente: mostra **desenhos
  do carro** (capô, teto, portas, paralamas, tampa traseira, laterais) e permite
  **`Incluir peça`** várias vezes, montando uma tabela `Serviços incluídos`.

#### 🔴 O que capturar aqui — três prints obrigatórios

| # | print | como fazer |
|---|---|---|
| 1 | **`Peça danificada` com a lista TODA aberta** | clique na lista e, sem escolher nada, tire o print. Se a lista for longa e não couber na tela, **role e tire 2 ou 3 prints**, nomeando `… lista de pecas ABERTA 1 de 3.png`, `2 de 3`, `3 de 3` |
| 2 | **`Motivo do dano` com a lista TODA aberta** — *depois* de já ter escolhido a peça | a lista de motivos muda por peça: para lataria vieram 7 opções, para vidro de porta 12, para lanterna 14. **São listas diferentes e queremos as três** |
| 3 | a tela preenchida, antes de avançar | HTML + print |

Nomes: `05 - passo 3 peca e causa.html` · `05 - passo 3 lista de pecas ABERTA.png` ·
`05 - passo 3 lista de motivos ABERTA.png`

> **Por que a lista aberta importa tanto:** cada apólice tem um catálogo próprio.
> Numa apólice Yelum vieram 21 peças; noutra, 30 — com para-choque, roda e
> pneu, que a primeira não tinha. O robô não pode decorar uma lista: ele tem de
> aprender a **ler** a lista de cada apólice. Para isso, precisamos ver várias.

### 2.6 · Tela: **Onde deseja realizar o serviço** (ainda no passo 3)

- **O que preencher:** **Estado** (a sigla: SC, SP, RJ…) · **Cidade** · **CEP**
  (opcional).
- ⚠️ **Preencha o CEP sempre que tiver.** É ele que faz o portal verificar se
  existe atendimento a domicílio na região — e domicílio é um dos pedaços que
  nunca capturamos.
- **Capturar:** HTML + print → `06 - onde realizar o servico`
  - 🔴 print a mais com a **lista de cidades aberta**.

### 2.7 · Tela: **Passo 4 — Confirme a peça danificada (80%)**

- **Endereço:** `#/<seguradora>/passo4/…`
- **O que aparece:** de 1 a 4 perguntas numeradas, **que mudam conforme a peça**.
  Exemplos já vistos:
  - vidro de porta: *"O vidro danificado tem película de controle solar
    (insulfilm)?"* · *"O vidro danificado é da porta dianteira ou traseira?"* ·
    *"Qual o lado do item danificado?"*
  - lanterna (Porto): uma pergunta só.
- ⚠️ **Esta tela NÃO aparece em lataria/martelinho.** Se ela não aparecer, não é
  erro — anote no resumo do fim (§6) que ela não apareceu.
- **O que fazer:** responder com o que o segurado disse.
  🔴 **Nunca escolha `Não sabe` só para destravar a tela.** `Não sabe` faz a
  seguradora pedir o vidro errado. Se o segurado realmente não souber, aí sim.
- **Capturar:** HTML + print → `07 - questionario 80`
  - 🔴 **um print por pergunta, com as opções à vista**, antes de responder.
    Se forem 3 perguntas, são 3 prints: `07 - questionario 80 - pergunta 1.png`,
    `… pergunta 2.png`, `… pergunta 3.png`.

### 2.8 · Tela: **Passo 5 — Nº do atendimento e escolha da loja (99%)**

- **Endereço:** `#/<seguradora>/passo5/…`
- 🔴 **AQUI NASCE O NÚMERO DO ATENDIMENTO.** Ele aparece no topo:
  `Nº do atendimento: ########`.
  **A partir deste instante o pedido existe na seguradora.** Desistir daqui em
  diante não apaga o pedido — cria um cancelado.
- **O que aparece abaixo do número:**
  - um cartão **`Serviço a domicílio`** — *"um técnico vai até o local de sua
    preferência"*, com os selos "Sem deslocamento · Economia de tempo" e um
    botão **`Agendar a domicílio`** (aparece **só** se o CEP tiver cobertura);
  - a **lista de lojas**, cada uma com nome, endereço, e os botões
    **`Consultar distância`** · **`Ver no mapa`** · **`Agenda disponível`** ·
    **`Agendar na loja`**;
  - o botão **`Cancelar atendimento`**.
- **O que fazer:** 🔴 **primeiro capture, depois clique.**
  1. **Print da tela inteira com o número do atendimento visível.** Se ela não
     couber, dois prints (topo e resto).
  2. HTML.
  3. **Clique em `Consultar distância` de uma loja** e tire print do resultado
     (vem uma distância em km e um tempo em minutos).
  4. **Clique em `Ver no mapa`** e tire print do mapa aberto.
  5. Só então siga para o agendamento.
- **Capturar:** `08 - passo 5 numero do atendimento e lojas.html` ·
  `08 - … .png` · `08 - consultar distancia.png` · `08 - ver no mapa.png`

⚠️ **Em lataria/martelinho esta tela não oferece escolha nenhuma** — o portal já
define a loja e vai direto para a conclusão. Se for isso que acontecer, anote.

### 2.9 · Telas: **Agendamento** — 🔴 O PEDAÇO QUE NUNCA CAPTURAMOS

Este bloco é a razão principal deste roteiro existir. **Em nenhuma das quatro
capturas alguém chegou a confirmar um agendamento.** Precisamos dos quatro
caminhos abaixo — não todos no mesmo acionamento, mas todos eventualmente.

#### 2.9.a — Agendar **na loja** (caminho principal)

1. Clique em **`Agenda disponível`** ou **`Agendar na loja`**.
2. Abre um **calendário**.
   🔴 **Print do calendário inteiro**, com os dias disponíveis marcados.
   ⚠️ Se o mês atual não tiver dia nenhum disponível, **passe para o mês
   seguinte** e tire print de novo, até achar um mês com dias livres. Numa
   captura anterior, o dia escolhido não tinha horário nenhum e a atendente
   desistiu — foi aí que perdemos tudo.
3. Escolha um dia.
4. Abre a **grade de horários**.
   🔴 **Print da grade com os horários visíveis.** Se aparecer vazia, volte e
   escolha **outro dia** — precisamos de uma grade **com horários**.
5. Escolha um horário.
6. Se aparecer uma janelinha **`Confirmar agendamento`** →
   🔴 **print ANTES de confirmar**, e depois confirme.
7. **Print da tela que aparece depois de confirmar.**
- **Capturar:** `09 - calendario.png` · `10 - grade de horarios.png` ·
  `11 - confirmar agendamento.png` · `12 - agendamento confirmado.html` + `.png`

#### 2.9.b — Agendar **a domicílio** (técnico vai até o segurado)

Só aparece se o CEP tiver cobertura.
1. Clique em **`Agendar a domicílio`**.
2. Capture **tudo** que vier: aviso das condições do serviço móvel, escolha de
   dia e hora, e 🔴 **se aparecer qualquer tela de valor, cobrança ou forma de
   pagamento — print obrigatório**. Nunca vimos essa tela.
3. Confirme e capture a confirmação.
- **Capturar:** `09d - domicilio condicoes.png` · `10d - domicilio dia e hora.png` ·
  `11d - domicilio formas de pagamento.png` · `12d - domicilio confirmado.html`

#### 2.9.c — Loja **credenciada** (quando a lista traz oficina parceira, não loja própria)

Às vezes a lista de lojas não tem agenda — só um botão de direcionamento.
🔴 Capture esse caminho também: print antes e depois do clique.
- **Capturar:** `09c - loja credenciada.png` · `10c - direcionamento confirmado.png`

#### 2.9.d — **Vistoria e envio de fotos** — 🔴 NUNCA CAPTURADO

Em algumas apólices, antes ou depois do agendamento, o portal pede uma
**vistoria**. Pode aparecer:
- um aviso explicando a vistoria;
- uma janelinha pedindo **um telefone** para enviar o link das fotos;
- uma tela para **anexar as fotos ali mesmo**.

🔴 **Se qualquer uma dessas aparecer, capture TUDO**, inclusive:
- o print da tela de anexar fotos **com uma foto já anexada**;
- se puder, **anexe uma foto de verdade e conclua** — é a única forma de
  aprendermos a mandar foto.
- **Capturar:** `13 - aviso de vistoria.png` · `14 - pedir telefone da vistoria.png` ·
  `15 - anexar fotos.png` · `16 - fotos enviadas.png`

> Esse é o link que hoje você cola à mão na conversa com o segurado. Capturando
> uma vez, o robô passa a gerar e mandar sozinho.

### 2.10 · Tela: **Solicitação concluída (100%)**

- **O que aparece:** *"Seu atendimento foi gerado com sucesso"* · o
  **Nº do atendimento** · a **Franquia** em reais · um bloco **`Próximo passo`**
  com **Loja / Endereço / Telefone** · um link **`acompanhar status`** · e os
  botões **`Dados do atendimento`** · **`Imprimir comprovante`** ·
  **`Cancelar atendimento`** · **`Novo atendimento`**.
- 🔴 **Espere a tela carregar INTEIRA antes de qualquer coisa.**
- **Capturar:** HTML + print → `17 - solicitacao concluida`

### 2.11 · **Comprovante** — 🔴 raramente capturado

1. Clique em **`Imprimir comprovante`**.
2. Vai abrir um PDF ou a janela de impressão. 👉 **Salve o PDF** dentro da pasta
   como `18 - comprovante.pdf`.
3. Clique também em **`Dados do atendimento`** e tire print do que abrir.
- **Capturar:** `18 - comprovante.pdf` · `19 - dados do atendimento.png`

### 2.12 · **Consultar atendimento** — 🔴 NUNCA CAPTURADO

Esta é uma captura **separada**, curta, que vale por si só.

1. Feche tudo e volte a `abraseuatendimento.com.br` com o **F12 aberto de novo**
   (§1.2), numa pasta nova: `YELUM - CONSULTAR ATENDIMENTO - 2026-09-15`.
2. Escolha a seguradora → **`Consultar atendimento`**.
3. Informe o que ele pedir (número do atendimento, CPF…).
4. **Capture cada tela**: o formulário de consulta, o resultado, o status.
5. Exporte o HAR.

> Isto é o que substitui o *"vou verificar com a seguradora e te aviso"*. Com
> essa tela mapeada, o sistema passa a acompanhar sozinho.

### 2.13 · **Área do Segurado**

Na tela de conclusão há o link **`acompanhar status`**, que leva a um site
diferente (a Área do Segurado). 🔴 **Clique nele, deixe carregar, e tire print.**
Não precisa salvar HTML.
- **Capturar:** `20 - area do segurado.png`

---

### Resumo da §2 — o checklist de uma captura completa

- [ ] F12 aberto, aba Network, `Preserve log` marcado, filtro vazio — **antes** de começar
- [ ] `01` menu da seguradora
- [ ] `02` passo 1 (CPF/placa/data) — + os botões de cobertura, se for Porto
- [ ] `03` modal dados da apólice
- [ ] `04` passo 2 + lista de tipo de telefone aberta
- [ ] `05` passo 3 + **lista de peças aberta** + **lista de motivos aberta**
- [ ] `06` onde realizar o serviço + lista de cidades aberta
- [ ] `07` questionário 80% — um print por pergunta
- [ ] `08` passo 5 com o **número do atendimento** + consultar distância + ver no mapa
- [ ] `09`–`12` agendamento (calendário → horários → confirmar → confirmado)
- [ ] `13`–`16` vistoria e fotos, se aparecer
- [ ] `17` solicitação concluída
- [ ] `18` comprovante em PDF · `19` dados do atendimento
- [ ] `20` área do segurado
- [ ] **HAR exportado com `with content`, antes de fechar a aba**

---

## 3. O que muda em cada serviço

A tela é sempre a mesma; muda a peça escolhida no passo 3 e, por causa dela, o
questionário do 80%. 🔴 **Em todos os serviços, sem exceção: print da lista de
peças aberta e da lista de motivos aberta.**

### 3.1 · PARA-BRISA ✅ **CAPTURA FEITA — 20/09/2026**

> ✅ **Esta captura já foi feita e já virou código.** O que ela respondeu, medido:
>
> - O questionário do para-brisa na Yelum tem **três** perguntas, uma de cada vez:
>   **posição do trincado** · **o trincado é maior ou menor que 10 cm?** · **o veículo
>   tem sensor de direção / mudança de faixa?**
> - 📊 Ele **NÃO** perguntou sensor de chuva, faixa degradê, antena nem aquecimento —
>   três das cinco perguntas que este roteiro esperava **não existem** nessa tela.
> - A medida dos **10 cm** está escrita **na própria pergunta do portal**. Não é regra nossa.
> - 🔴 O **reparo existe e é uma escolha do segurado**: quando a resposta é "menor", o
>   portal abre uma caixa oferecendo o reparo (grátis, ~30 min) e grava a resposta.
>   Por isso o robô passou a perguntar isso **na conversa, antes** de abrir o pedido.
> - Com o reparo aceito, o portal **fechou direto com uma loja, sem abrir agenda**.
>
> ⚠️ **O que esta captura NÃO respondeu:** as telas de agendamento (escolher dia e hora
> e confirmar) — porque não houve agenda. É exatamente o item **nº 1 da §5**.

O texto abaixo é o que se esperava antes da captura; fica como história.

### 3.1.a · PARA-BRISA — o que se esperava antes (13/09/2026)

- **Peça na lista:** `VIDRO PARABRISA` (aparece como `VIDRO DIANTEIRO`).
- **Nunca capturamos o questionário desta peça** — e é a peça mais comum.
- **Perguntas que esperamos ver** (pelo que você pergunta hoje ao segurado):
  - posição da trinca — motorista / carona / bordas / centro;
  - tamanho da trinca — provavelmente com uma medida (10 cm? 5 cm? uma moeda?);
  - **sensor de chuva** (as palhetas ligam sozinhas quando chove);
  - **faixa degradê** na parte de cima;
  - **sensor de direção / mudança de faixa** (ADAS).
  🔴 Se alguma dessas **não** aparecer, anote no resumo. E se aparecer alguma que
  não está nesta lista, **print dela com destaque**.
- **Atenção especial:** o portal pode oferecer **reparo** em vez de troca quando
  a trinca é pequena. Se aparecer qualquer tela ou aviso falando em **reparo**,
  **cola rápida** ou **sem franquia** → 🔴 print.

### 3.2 · VIDRO DE PORTA

- **Peça:** `VIDRO DE PORTA` (ou `VIDRO DE JANELA`, se for o vidrinho fixo).
- **Perguntas já conhecidas:** película (insulfilm)? · porta dianteira ou
  traseira? · qual o lado (motorista / carona)?
- **Atenção:** se o segurado disser que o vidro **não sobe/desce**, o problema
  pode ser a **máquina de vidro**, que é outra peça na lista
  (`MÁQUINA DE VIDRO ELÉTRICA/MANUAL`, `REPARO DE MÁQUINA…`). 🔴 Print da lista
  mostrando essas opções.

### 3.3 · VIGIA (vidro traseiro)

- **Peça:** `VIDRO VIGIA (TRASEIRO)` (aparece como `VIDRO TRASEIRO`).
- **Nunca capturamos o questionário.**
- **Esperamos ver:** película? · **desembaçador térmico** (aqueles fiozinhos)?

### 3.4 · RETROVISOR

- 🔴 **Aqui o difícil não é o questionário, é a LISTA.** A lista traz
  variações que você já pergunta ao segurado, cada uma é uma peça diferente:
  `RETROVISOR COMPLETO PINTADO COM PISCA` · `… SEM PINTURA COM PISCA` ·
  `… SEM PINTURA` · `CAPA DE RETROVISOR PINTADO…` · `CAPA … SEM PINTURA…` ·
  `LENTE DE RETROVISOR` · `PISCA DE RETROVISOR` — e ainda variações "EM LED".
- **Captura obrigatória:** 🔴 **a lista de peças aberta, rolada até o fim,
  fotografando TODAS as opções de retrovisor.** Esta é a captura que vale mais
  que o resto nesta peça.
- **No questionário, esperamos ver:** lado (motorista/carona) · talvez regulagem
  manual ou elétrica.

### 3.5 · FAROL

- **Mesma história do retrovisor:** a lista traz
  `FAROL PRINCIPAL CONVENCIONAL COM FEIXE EM LED` · `FAROL PRINCIPAL XENON` ·
  `FAROL PRINCIPAL LED ORIENTADO POR CÂMERA` · `FAROL MILHA/NEBLINA`.
  🔴 **Print da lista inteira aberta.**
- **Esperamos no questionário:** lado.
- ⚠️ **Se aparecer uma oferta de `polimento de farol`** (uma tela ou um aviso
  perguntando se quer polir) → 🔴 **print obrigatório**. É um serviço extra que
  sabemos existir e nunca vimos.

### 3.6 · LANTERNA

- **Lista traz:** `LANTERNA TRASEIRA BI-PARTIDA MALA` ·
  `LANTERNA TRASEIRA BI-PARTIDA LATERAL` · `LANTERNA TRASEIRA LED` ·
  `LANTERNA TRASEIRA NEBLINA` · `LANTERNA DIANTEIRA CONVENCIONAL` ·
  `LANTERNA TRASEIRA PARACHOQUE (RÉ/PISCA)`.
  👉 É exatamente a sua pergunta *"se for bipartida, é da tampa do porta-malas ou
  da carroceria?"* — **a resposta dela escolhe a peça na lista.**
  🔴 **Print da lista inteira aberta.**

### 3.7 · PARA-CHOQUE

- Pode aparecer de **duas formas diferentes**, dependendo da apólice:
  - como peça de troca: `PARACHOQUE PINTADO` / `PARACHOQUE SEM PINTURA`;
  - como reparo dentro de lataria: `REPARO DE PARACHOQUE DT` /
    `REPARO DE PARACHOQUE TR`.
  🔴 **Anote no resumo qual das duas apareceu** e print da lista.

### 3.8 · LATARIA / PINTURA / MARTELINHO

- **Peça:** `REPARO DE LATARIA E PINTURA`.
- **A tela é diferente:** aparecem **desenhos do carro** com as partes
  nomeadas (capô, teto, tampa traseira, paralamas, portas, laterais, colunas),
  e você escolhe peça + motivo e clica **`Incluir peça`**, montando a tabela
  **`Serviços incluídos`**.
  🔴 **É o único serviço com VÁRIAS peças no mesmo atendimento.**
- **Capturar:** print dos desenhos · print da lista de peças aberta ·
  🔴 **print da tabela `Serviços incluídos` com pelo menos 2 ou 3 peças dentro**.
- **Não tem questionário de 80%** e **não tem escolha de loja** — a seguradora
  define a loja e manda por e-mail/SMS. Isso já está medido; confirme que se
  repete.
- ⚠️ Se aparecer uma pergunta sobre **tamanho do amassado** (menor que 5 cm /
  entre 5 e 20 / maior que 20) → 🔴 print.

### 3.9 · RODA / PNEU / SUSPENSÃO

- **Existe só onde a apólice tiver essa cobertura.** Na **Porto** é uma escolha
  explícita no passo 1.
- 🔴 **Nunca capturamos este fluxo funcionando** — a única tentativa deu
  "sem cobertura" e morreu no passo 1.
- **Precisamos de:** uma apólice **com** essa cobertura, do início ao fim.
- A lista traz `PNEU` · `RODA LIGA LEVE` · `RODA FERRO` ·
  `RODA, PNEU E SUSPENSÃO`. 🔴 Print da lista aberta.

### 3.10 · Outros que podem aparecer

Se a lista da apólice trouxer `TETO SOLAR`, `TETO PANORÂMICO`,
`REPARO DE ARRANHÕES`, `MARTELINHO` (reparo de amassado) —
🔴 **capture mesmo sem acionar**: só o print da lista já serve.

---

## 4. O que muda em cada seguradora

### 4.1 As 38 seguradoras que o portal atende hoje

📊 Lista lida do próprio portal em 09/09/2026.

| # | seguradora | # | seguradora |
|---|---|---|---|
| 1 | Alfa Seguradora | 20 | Neo Seguros |
| 2 | Aliro | 21 | Pier |
| 3 | Allianz | 22 | **Porto Seguro** |
| 4 | AXA | 23 | RPS Administradora |
| 5 | **Azul Seguros** | 24 | Sancor Seguros |
| 6 | Banestes Seguros | 25 | Santander Auto |
| 7 | BB Seguros | 26 | Sem Parar |
| 8 | BP Seguradora | 27 | Serasa |
| 9 | **Bradesco Seguros** | 28 | Sompo Seguros |
| 10 | BVIX | 29 | Split Risk |
| 11 | Caixa Seguradora | 30 | SulAmérica |
| 12 | Darwin Seguros | 31 | **Tokio Marine** |
| 13 | Gringo | 32 | Too Seguros |
| 14 | **HDI Seguros** | 33 | Toyota Seguros |
| 15 | Indiana Seguros | 34 | Usebens |
| 16 | Ituran | 35 | Usebens / Nubank |
| 17 | Justos | 36 | **Yelum** (aparece como **Liberty**) |
| 18 | **Mapfre** | 37 | Youse |
| 19 | Mitsui Sumitomo | 38 | **Zurich** |

Além dessas, o portal tem endereços preparados para mais quatro que não
apareceram na lista do dia: **Bllu**, **Generali**, **Grupo HDI** e
**Zurich Santander**. Se alguma delas aparecer na tela algum dia → 🔴 print.

### 4.2 Cuidados por seguradora

| seguradora | o que muda / cuidado |
|---|---|
| **Porto Seguro** | 🔴 **Única com o seletor de cobertura no passo 1** (`Vidros, faróis/lanternas e retrovisores` × `Roda, pneu e suspensão`). Tudo depois disso é igual às outras. Print obrigatório dos dois botões |
| **Yelum** | 🔴 **No portal ela se chama `Liberty`.** Não existe "Yelum" na lista — procure por **Liberty** |
| **Sompo** | ⚠️ Pode haver **duas** entradas parecidas na lista. Se aparecerem duas, 🔴 **capture as duas telas seguintes** (a de menu de cada uma) e anote qual você usou. Por dentro elas apontam para lugares diferentes |
| **Bradesco Seguros** | 🔴 **Caso especial — leia a §4.4** |
| **Zurich / Zurich Santander** | se aparecerem as duas, mesmo cuidado da Sompo |
| **HDI / Grupo HDI** | idem |
| todas as outras | nada especial esperado — mas se a tela for diferente do que este roteiro descreve, **isso é o achado**: print e anotação |

### 4.3 Prioridade — por onde começar

```
1º  YELUM (Liberty)  — PARA-BRISA, do início ao agendamento confirmado
2º  YELUM (Liberty)  — a mesma coisa escolhendo DOMICÍLIO
3º  PORTO SEGURO     — qualquer vidro, até o agendamento confirmado
4º  AZUL e ZURICH    — só até o passo 3 (são as que já atendem vidros por WhatsApp)
5º  BRADESCO         — o teste duplo da §4.4
6º  HDI · TOKIO MARINE · MAPFRE · ALLIANZ · ALFA
        — só o passo 1 + a lista de peças aberta. 5 minutos cada
7º  as 27 restantes  — mesma coisa, quando sobrar tempo
```

> Para as prioridades 4, 6 e 7 **não é preciso abrir pedido nenhum**: basta
> chegar ao passo 3, abrir a lista de peças, tirar o print, **desistir do
> atendimento pelo botão do portal** e exportar o HAR. Nenhum pedido nasce antes
> do passo 5, então essas capturas são inofensivas.

### 4.4 🔴 Bradesco — o teste duplo

A Bradesco aparece em **dois lugares** e não sabemos qual é o certo:

**Teste A — no portal próprio**
1. Pasta: `BRADESCO - VIDRO - agendeseuservico - 2026-09-__`
2. F12 aberto → `https://www.agendeseuservico.com/`
3. Faça o acionamento até onde conseguir, capturando cada tela como na §2.
4. Exporte o HAR.

**Teste B — no portal de sempre**
1. Pasta: `BRADESCO - VIDRO - abraseuatendimento - 2026-09-__`
2. F12 aberto → `abraseuatendimento.com.br` → escolha **Bradesco** na lista.
3. Vá até o passo 1 e preencha CPF + placa + data.
4. 🔴 **O que interessa é o que acontece aqui:** ele aceita e segue, ou dá erro?
5. Print da resposta, seja qual for. Exporte o HAR.

**No resumo do fim, escreva em uma linha:**
> `Bradesco: o agendeseuservico [aceitou / não aceitou]; o abraseuatendimento
> [aceitou / não aceitou]. O que eu usaria de verdade é ____.`

---

## 5. O QUE AINDA FALTA CAPTURAR — em ordem de valor (v2.0 · 21/09/2026)

> 🔴 **Leia esta ordem como ela está.** A nº 1 vale mais que todas as outras juntas:
> sem ela o robô **não pode marcar dia e hora** para ninguém, e é isso que sobra de
> trabalho manual em cima de você.
>
> **Em TODAS elas, sem exceção:** grave o **HAR "with content"** ligado **antes** de
> escolher a seguradora (§1.2 e §1.6), salve o **HTML de cada tela** (§1.3) e mande
> junto um **TXT** com a estrutura da apólice (seguradora, tipo de veículo, o que a
> apólice cobre) — **não precisa de vídeo**.

---

### ✅ 1 · UM AGENDAMENTO LEVADO ATÉ O FIM — a captura nº 1

**O que fazer, exatamente:**

1. Na **Yelum**, abra um acionamento de **vidro de PORTA** ou de **VIGIA** (o vidro
   traseiro), com o vidro **quebrado ou trincado grande** — **não** uma trinca
   pequena. Trinca pequena vira reparo, e reparo **fecha sem agenda** (já sabemos).
2. Escolha uma cidade **que tenha loja** (uma cidade grande da região).
3. Vá até o fim, **sem desistir**:
   - escolha a **loja** na lista (print da lista inteira, com distância e endereço);
   - escolha um **dia** no calendário (print do calendário com os dias livres);
   - escolha um **horário** na grade (print da grade cheia);
   - clique em **CONFIRMAR** e espere a tela de conclusão aparecer inteira.
4. ⚠️ **Se não aparecer nenhum horário, troque de dia** — vá testando até achar um dia
   com horário livre. Se nenhum dia tiver, anote isso no resumo e avise: é fato novo.
5. Salve também a **tela final** (HTML + print) e, se houver, o **comprovante**.

**Por que ela vale tanto:** o botão de confirmar agendamento **nunca foi capturado**.
📊 Nas 5 capturas que temos, ele tem **zero** ocorrências — e por isso o robô está
proibido de usá-lo. Com esta captura, ele passa a marcar dia e hora sozinho.

---

### 2 · A MESMA COISA, mas escolhendo a loja SEM agendar

Se, na tela das lojas, o portal oferecer algo como **"direcionar para a loja"** (em vez
de "agendar"), faça esse caminho numa segunda vez e vá até o fim. É um botão diferente
do nº 1, e também nunca foi visto.

---

### 3 · UM CASO EM QUE O PORTAL PEÇA FOTOS OU VISTORIA

**O que fazer:** abra um acionamento em que você **desconfie** que vai pedir vistoria e
siga até a tela de fotos aparecer. Salve a tela do pedido de vistoria, a tela de
**anexar fotos** e o que vier depois.

💭 **Candidatos** (palpite, não medido): **farol LED / Matrix**, **retrovisor com LED**,
e a **Porto** de modo geral. Se você já souber de uma peça que sempre pede vistoria,
use essa — e escreva no resumo qual foi.

**Por que:** o portal tem um ramo inteiro de vistoria que o robô lê e **não conhece** —
📊 zero ocorrências nas 5 capturas. Hoje todo caso desses para e vira trabalho seu.

---

### 4 · SERVIÇO A DOMICÍLIO, NUMA CAPITAL

**O que fazer:** abra um acionamento usando um **CEP de capital** (onde o atendimento em
casa costuma existir) e vá até a tela em que o portal ofereça **"a domicílio"**. Salve:
o cartão da oferta, as condições, o dia/hora do técnico e a confirmação.

📊 Nas capturas que temos, o portal respondeu **"não atende a domicílio"** nesse CEP —
então a tela nunca apareceu. É a opção mais confortável para o segurado e o robô nem
sabe que ela existe.

---

### 5 · A LISTA DE MOTIVOS DE CANCELAMENTO — **só olhar, não cancelar**

**O que fazer:** num atendimento já aberto (pode ser um de teste), com o HAR **gravando**,
clique em **cancelar** até a tela que mostra a **lista de motivos**, tire o print da
lista aberta… e **NÃO confirme**. Feche a tela.

**Por que:** o robô conhece **um** código de motivo, tirado do programa do portal, e
nunca viu a lista de onde ele sai. Cancelar com o motivo errado deixa registrado na
seguradora uma razão que não é a verdadeira.

---

### 6 · UM ACIONAMENTO DE VIGIA, UM DE FAROL E UM DE RETROVISOR — até o 80 %

**O que fazer:** três acionamentos separados (qualquer seguradora), cada um indo até a
tela das **perguntas específicas** (os 80 %) e **parando ali, sem enviar**. Print de
**cada pergunta** e de **cada lista de opções aberta**.

**Por que:** 📊 só conhecemos o questionário do **para-brisa** e do **vidro de porta**.
Vigia, farol, retrovisor, teto e para-choque nunca foram vistos — e toda pergunta
desconhecida faz o robô parar **depois** de o pedido já existir, que é o pior momento.

---

### 7 · UM ACIONAMENTO EM OUTRA SEGURADORA — pelo menos o passo 1 e a lista de peças

**Qual:** **Porto** (esta, se possível, completa), **Azul**, **Tokio Marine**, **HDI** ou
**Allianz** — qualquer uma delas serve; duas é melhor que uma.

**O mínimo aceitável:** o **passo 1** (CPF, placa, data) e a **lista de peças aberta**
(print da lista inteira, rolando até o fim).

**Por que:** 📊 o portal publica **38** seguradoras e nós só medimos **duas**. O robô já
abre pedido em todas elas, mas o **questionário** de cada uma é desconhecido.

---

### 8 · UM ATENDIMENTO ABERTO POR OUTRA CORRETORA

**O que fazer:** o mesmo roteiro, feito por **outra corretora** (outro acesso ao portal).
Pode ser o caso mais simples que houver.

**Por que:** todas as capturas que temos vêm do mesmo acesso. O portal identifica a
corretora no começo, e não sabemos o que muda com outra. O produto é para **qualquer**
corretora, e foi provado com uma só.

---

### Ficou de fora desta lista (continua valendo, mas depois)

**Bradesco** (o teste duplo da §4.4 — ainda pode ser outro sistema), **roda/pneu/suspensão**
na Porto com apólice que cubra, **lataria com várias peças**, e a tela
**"Consultar atendimento" / Área do Segurado** — esta última sobe de prioridade **na
hora em que alguém responder** se dá para retomar um atendimento parado pelo número
(é a pergunta nº 12 do arquivo `PERGUNTAS-PARA-A-ATENDENTE-PORTAL-DE-VIDROS.md`).

---

## 6. O que enviar ao Founder no fim

1. **Confira a pasta** — tem de ter: o `.har` (grande, 10–30 MB), os `.html` com
   suas pastas `_files`, os `.png` e, se houver, o `.pdf` do comprovante.
2. **Zipe a pasta**: botão direito sobre ela → **Enviar para** → **Pasta
   compactada**. O zip fica com o mesmo nome da pasta.
3. **Mande o zip** pelo canal combinado com o Founder.
4. **Junto do zip, mande uma linha de resumo** neste formato:

```
Seguradora: ______
Serviço: ______
Cheguei até: ______  (ex.: "agendamento confirmado" / "passo 5, cancelei" / "erro no passo 1")
Nº do atendimento: ______  (ou "não chegou a gerar")
O que estranhei: ______
```

Exemplo de como fica preenchido:

> Seguradora: Yelum (Liberty)
> Serviço: para-brisa
> Cheguei até: agendamento confirmado na loja
> Nº do atendimento: [o número]
> O que estranhei: o primeiro dia do calendário não tinha horário nenhum, tive
> que pular para o dia seguinte. E apareceu uma pergunta sobre sensor de chuva
> que eu não esperava.

🔴 **O "o que estranhei" é a parte mais útil do resumo.** Tudo que fugiu do que
este roteiro descreve é exatamente o que o sistema ainda não sabe. Escreva mesmo
que pareça bobagem.

---

## 7. O que NÃO fazer

| ❌ | por quê |
|---|---|
| **Não assista ao vídeo do portal com o F12 aberto** | 📊 Na captura de 09/09, o vídeo institucional entrou na gravação com **38 registros** de YouTube misturados no meio da conversa com a seguradora. Não estraga, mas suja. Se quiser ver o vídeo, veja **antes** de abrir o F12 |
| **Não feche a aba antes de exportar o HAR** | 🔴 Fechou, perdeu. Não tem como recuperar. **Exportar é a última coisa que você faz** |
| **Não cancele nem desista antes da última tela carregar** | O número do atendimento nasce no meio do caminho. Cancelar depois dele não apaga o pedido, e ainda nos faz perder as telas do fim, que são as que faltam |
| **Não edite o arquivo `.har`** | Ele parece texto, mas qualquer letra mudada quebra o arquivo inteiro. **Não abra, não "limpe", não apague nada.** Mande como saiu |
| **Não digite nem cole senha em lugar nenhum deste processo** | O portal de vidros não pede login. Se alguma tela pedir usuário e senha, 🔴 **pare, tire print da tela e avise o Founder antes de digitar qualquer coisa** |
| **Não renomeie os arquivos depois** | O nome tem de refletir a ordem real em que as telas apareceram. Renomear depois embaralha o caminho |
| **Não apague a pasta `_files` que nasce junto do HTML** | Ela é metade da captura |
| **Não junte dois acionamentos na mesma pasta** | Um acionamento, uma pasta, um HAR |
| **Não escreva nada no campo de filtro do Network** | Filtro escrito = gravação incompleta, e só se descobre depois |

---

## Cola de bolso — para imprimir e deixar do lado

```
ANTES        pasta "SEGURADORA - SERVIÇO - AAAA-MM-DD"
             F12 → aba Network → marcar "Preserve log" → filtro vazio
             (só então clicar em Iniciar atendimento)

EM CADA TELA Ctrl+S → "Página da Web, completa" → NN - nome da tela.html
             Win+Shift+S → print

LISTA ABERTA obrigatório em: peça danificada · motivo do dano · tipo de telefone
             · cidade · lojas · calendário · grade de horários

NUNCA        cancelar/fechar antes da última tela carregar

NO FIM       Network → ⬇️ → "Save all as HAR WITH CONTENT"
             zipar a pasta + a linha de resumo
```

---

*Escrito a partir de quatro capturas medidas (dois acionamentos Yelum, dois
Porto), do HTML das telas salvas, do código do próprio portal e de
`docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`. Nenhum dado de segurado,
número de atendimento real ou credencial aparece neste documento.*
