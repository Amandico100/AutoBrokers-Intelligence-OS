# O portal de vidros, tela por tela — o mapa MEDIDO

> `https://abraseuatendimento.com.br` · **Maxpar Assistências** + **Grupo Autoglass**,
> operando por dentro da marca de cada seguradora.
>
> 📊 **Fonte primária:** captura de tela a tela feita pelo Founder em 06/07/2026,
> com apólice real, em **Yelum** (percurso completo até o protocolo) e **Tokio
> Marine** (até o 80%, sem enviar). Porto Seguro: só a tela de cobertura.
> 📊 **Fonte secundária:** 39 `portal_jobs` de `vidros_lanternas` (06 a 15/07),
> Supabase `dcajcvlzcjbmyapmklil` — nomes reais de campo e onde cada um parou.
>
> Este arquivo é a **autoridade sobre o que o portal pergunta**. Código que
> discordar dele está errado até que uma medição nova diga o contrário.

---

## 1. O portal não é da seguradora

A marca muda; o motor não. A URL é `#/<slug>/passoN` e o `<slug>` é a única
coisa que varia entre Yelum, Tokio, Porto. **Um corredor serve todas** — e é
por isso que ele vale a pena: 📊 a lista do primeiro dropdown tem dezenas de
seguradoras (ALFA, ALIRO, ALLIANZ, AXA, AZUL… e segue).

Duas consequências que mudam o desenho:

1. **Uma correção conserta todas as seguradoras de uma vez.** É o oposto do
   corredor de WhatsApp, onde cada seguradora tem texto próprio.
2. **Uma diferença de tela é exceção, não regra.** Vale registrar a exceção,
   nunca reescrever o mapa.

---

## 2. A sequência

| # | URL | Tela | O que trava |
|---|---|---|---|
| 0 | `#/` | Selecione a seguradora | — |
| 1 | `#/<slug>/menu-atendimento` | Iniciar / Consultar atendimento | — |
| 2 | `#/<slug>/passo1` | CPF/CNPJ + placa + data do dano | apólice não localizada |
| 2b | *modal lateral* | **Dados da apólice** → Confirmar | dado divergente |
| 3 | `#/<slug>/passo2/<uuid>` | Confirme seus dados (20%) | e-mail/telefone/relação |
| 4 | `#/<slug>/passo3/<uuid>` | Nos conte o que aconteceu (50%) | peça · causa · local · descrição |
| 5 | *mesma rota* | Onde deseja realizar o serviço | estado · cidade · CEP |
| 6 | `#/<slug>/passo4/<uuid>` | **Confirme a peça danificada (80%)** | perguntas específicas |
| 7 | `#/<slug>/passo5/<uuid>` | **Nº do atendimento** + escolha da loja | agenda / domicílio |

### 🔴 O passo 7 nunca foi alcançado

📊 **39 acionamentos. Zero protocolos. Zero com `confirm=true`.**
33 pararam em `needs_human`, 5 falharam, e o único `done` também não tem
protocolo. **O portal nunca chegou a abrir um pedido de verdade.**

Isso é bom: significa que nenhum segurado foi prejudicado. E significa que
tudo abaixo do passo 6 é **mapa, não histórico**.

---

## 3. A regra que muda o produto inteiro

> **"O atendimento web permite apenas a SELEÇÃO de 1 (um) ITEM para
> TROCA/REPARO por atendimento."**
> **"Se o item escolhido possuir lateralidade (por exemplo, lado esquerdo e
> lado direito), será necessário abrir uma nova solicitação para o outro lado."**

📊 Texto literal, presente em **todas** as telas do fluxo.

**Dois vidros quebrados = dois acionamentos = dois protocolos.** Um segurado
que diz *"quebraram o vidro dos dois lados"* não é um pedido; são dois. Um
sistema que não sabe disso abre um, avisa o cliente que está resolvido, e o
outro lado fica quebrado — e ninguém descobre até o vidraceiro chegar.

---

## 4. Tela a tela: o que exatamente é perguntado

### Passo 1 — quem é o carro

| Campo | Seletor 📊 | Origem do dado |
|---|---|---|
| CPF/CNPJ (solicitante) | `#inserir-cpf-input` | **do segurado**, da conversa |
| Placa do veículo (segurado) | `#input_1` | InfoCap `/itens` |
| Data do dano ao veículo | `#input_3` (datepicker Material) | conversa |

⚠️ O rótulo diz *"CPF/CNPJ (solicitante)"* mas o valor esperado é o do
**titular da apólice** — é assim que a apólice é localizada. O solicitante de
verdade só aparece no passo 2. **Rótulo mentiroso é armadilha de leitura.**

Só a **Porto** acrescenta aqui: *"Selecione a cobertura desejada"* —
`Vidros, faróis/lanternas (e retrovisores)` ou `Roda, pneu (e suspensão)`.
📊 Yelum e Tokio não oferecem roda/pneu.

### Passo 2b — o modal que ninguém pode pular

**Dados da apólice**: nome do segurado · nome social · placa (mascarada
`Q***A91`) · apólice (`******261149211`) · veículo · últimos 6 dígitos do
chassi. Botões **Voltar** / **Confirmar**.

É a única checagem de que **abrimos o pedido do carro certo**. O que ele
mostra é exatamente o que a InfoCap já nos deu — então dá para **conferir**,
não só clicar. Divergência aqui é handoff, nunca "Confirmar assim mesmo".

### Passo 3 (20%) — quem está pedindo

| Campo | Nome real 📊 | O que preenchemos |
|---|---|---|
| Sua relação com o titular | `segr` | **Corretor** |
| E-mail | `email-segurado-input` | e-mail da corretora |
| ☑ O e-mail informado pertence ao corretor | — | **marcar** |
| Seu nome completo (solicitante) | `nome-solicitante-input` | nome da corretora |
| CPF ou CNPJ (solicitante) | `cpf-cnpj-solicitante-input` | CNPJ da corretora |
| Telefone | `telefone-input` | telefone da corretora |
| Tipo de telefone | `TipoTelefoneSolicitante0` | qualquer válido |
| ☐ Quero receber atualizações via WhatsApp | — | ver §6 |

📊 As opções de relação são: *Selecione uma opção · O próprio · Cônjuge ·
Filho · **Corretor** · Outros*. **Corretor existe e é o nosso caso.**

### Passo 4 (50%) — o que aconteceu

Desenho do carro que **pinta a peça escolhida** — é feedback visual para
humano, não fonte de dado.

| Campo | Nome real 📊 | Natureza |
|---|---|---|
| Qual foi a peça danificada? | `qualItemDanificado` | 🔴 **crítico** |
| Como ocorreu o dano ao veículo? | `comoOcorreuDanoVeiculo` | 🔴 **crítico** |
| Onde ocorreu o dano ao veículo? | `ondeOcorreuDano` | urbano / rodoviário |
| Descreva como aconteceu | `descrever-acontecimento-textarea` | **mín. 30 / máx. 2000** |

📊 Peças vistas: `VIDRO PARABRISA` · `VIDRO DE PORTA` · `VIDRO DE JANELA` ·
`VIDRO VIGIA (TRASEIRO)`.

🔴 **A lista de "como ocorreu" MUDA conforme a peça.** Palavras do Founder:
*"quando escolho parabrisas vem algumas situações para escolher em Como
ocorreu o dano ao veículo? São diferentes da situação dos vidros laterais."*
Logo: **ler a lista na tela, sempre.** Uma tabela decorada de causas seria
falsa metade das vezes.

### Passo 5 — onde consertar

Estado (**sigla**, `SC`) · Cidade · **CEP (opcional)**.

📊 O rótulo do CEP diz o que ele faz: *"Informe seu CEP para encontrarmos a
unidade mais próxima e verificar se há disponibilidade de atendimento em
domicílio na sua região."*

**"Opcional" no portal, obrigatório para nós.** Sem CEP não há atendimento a
domicílio, e domicílio é o que transforma o serviço em conveniência. Nós temos
o CEP na InfoCap. Não mandá-lo é jogar fora vantagem de graça.

### Passo 6 (80%) — as perguntas específicas 🔴

**São condicionais e progressivas: a pergunta 2 só nasce depois da 1.**
Não dá para preencher em bloco — o portal revela uma de cada vez.

**Vidro de porta** (📊 Yelum):
1. O vidro danificado tem película de controle solar (insulfilm)? → SIM · NÃO · Não sabe
2. O vidro danificado é da porta dianteira ou traseira? → DIANTEIRA · TRASEIRA · Não sabe
3. Qual o lado do item danificado? → **Lado do carona** · **Lado do motorista** · Não sabe

**Parabrisa** (📊 Tokio):
1. Poderia informar a posição do trincado? → Em frente ao motorista · Em frente ao carona · Nas bordas · No centro · Não sabe
2. O trincado está maior ou menor que 10 cm? → **Maior (troca do vidro)** · **Menor (possibilidade de reparo)** · Não sabe
3. A versão do veículo é comfortline? → Sim · Não · Não sabe

Três coisas a aprender daqui:

**(a) "Não sabe" está sempre disponível — e é uma armadilha.**
Ele destrava a tela e degrada o serviço: o portal deixa de saber qual vidro
pedir. *Nunca* responder "Não sabe" enquanto pudermos perguntar ao segurado.
Responder "Não sabe" por preguiça do robô é diferente de responder "Não sabe"
porque o segurado realmente não sabe. **Só a segunda é honesta.**

**(b) A pergunta 3 do parabrisa é sobre a VERSÃO DO CARRO** — `comfortline`,
uma versão da Volkswagen. É pergunta de **apólice**, não de dano: está no
campo `Veículo` da InfoCap (*"NIVUS COMFORTLINE 1.0 200 TSI FLEX AUT"*).
Perguntar isso a um segurado assustado é ridículo — e a resposta já está na
nossa mão.

**(c) Maior/menor que 10 cm decide troca × reparo.** Não é burocracia: é o
serviço que será prestado. Errar aqui manda o vidraceiro com a peça errada.

### Passo 7 — o protocolo e a loja

📊 **O `Nº do atendimento` aparece AQUI, no topo da tela — antes da escolha da
loja.** No exemplo: `22842291`.

> **O pedido já existe na seguradora antes de escolhermos onde consertar.**

É o fato mais importante de todo este documento. Ele significa que:
- **capturar o protocolo não pode esperar** o fim do fluxo;
- **desistir depois daqui não desfaz nada** — cria um atendimento cancelado;
- **repetir o fluxo cria um segundo atendimento**, não corrige o primeiro.

Opções de conclusão:
- **Serviço a domicílio** — *"Agendar a domicílio"*, com os selos "Sem
  deslocamento · Economia de tempo · Atendimento premium";
- **Loja** — ex. `AUTOGLASS MG19`, Rua Camilo Veríssimo da Silva 555, Rocado,
  São José/SC 88108-250, com *Consultar distância*, *Ver no mapa*,
  *Agenda disponível*, *Agendar na loja*.

Cancelar exibe: *"Ao confirmar o cancelamento, você não utilizará o serviço de
sua seguradora para esse atendimento, deseja confirmar?"* → e a tela final
oferece **Dados do atendimento**, **Solicitar novo atendimento**, **Imprimir
comprovante** e um link de acompanhamento.

---

## 5. "Consultar atendimento" — o acompanhamento existe

📊 Passo 1 do portal oferece **Consultar atendimento** ao lado de Iniciar. E a
tela final diz *"Para você acompanhar o status do seu atendimento é só clicar
aqui."*

Ou seja: o *acompanhar até o fim* que prometemos ao segurado **tem uma fonte
real** — não precisa ser inferido nem perguntado à seguradora por WhatsApp.
Ainda não está mapeado (o Founder não capturou essa tela). Fica registrado
como o próximo pedaço de mapa a levantar.

---

## 6. A caixa do WhatsApp — a decisão do Founder

📊 Existe `☐ Quero receber atualizações do meu atendimento via whatsapp`.

Decisão registrada, nas palavras dele: *"só se colocar o número do CLIENTE. Se
colocar o número do agente ou da corretora, vai ser muita confusão recebendo
várias informações diferentes do mesmo lugar."*

Regra: **marcar apenas com o telefone do segurado, e avisá-lo antes.** Nunca
com o número da corretora — o portal escreveria no mesmo WhatsApp por onde o
nosso agente fala, e ninguém saberia quem disse o quê.

⚠️ Mas o telefone do passo 2 é o do **solicitante** (a corretora). Marcar a
caixa mandaria as atualizações para a corretora. **Enquanto não houver campo
separado para o telefone do segurado, a caixa fica desmarcada.**

---

## 7. O que ainda não foi medido

| Lacuna | O que destrava |
|---|---|
| Telas de **roda/pneu/suspensão** (só Porto) | uma captura na Porto |
| Lista completa de "como ocorreu" por peça | ler na tela — **de propósito** |
| Perguntas específicas de **retrovisor, farol, lanterna, vigia, teto** | captura ou primeira execução real |
| Tela **Consultar atendimento** | uma captura |
| Quais seguradoras da lista **realmente atendem** vidros | tentativa por seguradora |
| Diferenças de **Porto** depois do passo 1 | captura |

**Nenhuma delas impede o corredor de funcionar** — todas caem no caminho
adaptativo, que lê a tela real. Elas só definem quanto o robô vai precisar
pensar em vez de reconhecer.

---

## 8. Por que os 39 pararam — a autópsia, uma a uma

📊 Consulta em 04/08/2026 sobre `evidence->>'message'` dos 39 jobs de
`vidros_lanternas`. **O resultado desmente a leitura de que "não funciona".**

| Motivo | n | O que realmente é |
|---|---|---|
| *"cheguei na confirmação (80%) — aprove para enviar"* | **9** | ✅ **sucesso.** Percorreu tudo e parou no freio, como projetado |
| *"muitos passos sem concluir"* | 9 | estourou o teto de 22 passos |
| *"preciso de: …"* | 9 | ver abaixo — **são duas coisas diferentes** |
| *"tela travada: repetiu …"* | 7 | repetiu ação que **já tinha dado certo** |
| (sem mensagem) | 4 | jobs antigos, antes da evidência estruturada |
| *"click Avançar → click_notfound"* | 3 | botão não encontrado pelo rótulo |

### 9 de 39 chegaram ao fim do trabalho

**Quase um quarto atravessou o formulário inteiro** e parou porque
`confirm=False` está cravado no código. Isso não é falha: é o freio segurando.
Dizer "zero protocolos" é verdade e é enganoso — nunca pedimos protocolo nenhum.

### O cérebro pedia o que já tinha na mão — mas só em 4 dos 9

📊 Cruzando a pergunta com o `params` do mesmo job:

| O cérebro perguntou | Tinha no payload? |
|---|---|
| *"Qual é o tipo de telefone do segurado?"* | ✅ nome, apólice, CEP, estado |
| *"Qual o tipo de atendimento que deseja?"* (2×) | ✅ tudo |
| *"Qual o tipo de dano no vidro da porta?"* | ✅ tudo |
| *"Qual o número da apólice?"* (3×) | ❌ **payload vazio** |
| *"Qual é o nome do segurado?"* | ❌ **payload vazio** |
| *"Qual o CEP do segurado?"* | ❌ **payload vazio** |

**São dois defeitos, não um.**

**(a) 4 vezes o cérebro tinha o dado e perguntou assim mesmo.** O prompt do
sistema proíbe *literalmente* perguntar tipo de telefone — *"JAMAIS use
ask_human para campos de FORMATO onde qualquer valor serve"* — e ele perguntou.
Em outra, mandou `Santa Catarina` num autocomplete onde o prompt manda usar a
**sigla**. E em 7 paradas ele repetiu uma ação que voltou `filled` /
`mdselect=corretor`, ou seja, **que tinha funcionado**.

📊 Não foi falta de cérebro: **zero** jobs registram `cerebro de visao
indisponível` ou `nao consegui decidir`. Ele estava lá, com a instrução na
frente, e não seguiu.

O cérebro que dirige o portal é `gpt-4o-mini` (o padrão de
`PORTAL_VISION_MODEL`) — um modelo pequeno conduzindo uma tarefa agêntica de
22 passos com 1.500 caracteres de instrução. É a explicação mais simples que
cobre os três sintomas ao mesmo tempo.

**(b) 5 vezes o dado não existia.** `segurado.nome`, `apolice` e `cep` nulos =
a InfoCap não respondeu, e o acionamento **nasceu assim mesmo**. Perguntar era
a única coisa honesta a fazer ali — o defeito foi deixar o job nascer sem os
fatos.

### O que isso ensina, e vale além de vidros

> **Fato conhecido não deve passar por um modelo.**

Nome da corretora, e-mail, CNPJ, relação (`Corretor`), nome do segurado,
apólice, CEP, estado, cidade: **cada um tem um único valor certo, sabido antes
de a tela abrir.** Mandar um modelo "decidir" preenchê-los cria três riscos de
graça — ele pergunta o que sabe, erra o formato, ou gasta passos do teto.

📊 E o teto foi atingido **9 vezes**. Cada campo preenchido por código é um
passo que não é gasto.

O cérebro deve decidir só o que é **julgamento**: peça, causa, local, descrição
e as respostas específicas do 80%. Nada mais.

---

## 9. O que este mapa proíbe

1. **Decorar a lista de causas.** Ela muda por peça e por seguradora. Ler.
2. **Responder "Não sabe" para destravar.** É perda de serviço disfarçada de progresso.
3. **Perguntar ao segurado o que está na apólice.** Versão, placa, chassi, CEP: temos.
4. **Tratar dois lados como um pedido.** O portal proíbe; nós avisamos antes.
5. **Reexecutar um acionamento que passou do 80%.** Cria pedido novo, não corrige o velho.
6. **Marcar a caixa do WhatsApp com o telefone da corretora.**
