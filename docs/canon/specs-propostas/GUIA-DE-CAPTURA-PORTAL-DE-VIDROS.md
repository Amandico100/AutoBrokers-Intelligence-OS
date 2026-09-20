# Guia de captura — Portal de Vidros (cartão de bolso)

> **Para quem é:** Regina, e o Founder lê junto.
> **O que é:** a versão curta, à prova de erro, do que fazer antes / durante / depois de um acionamento no portal.
> **A versão longa, tela por tela**, continua sendo `docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md` —
> este cartão não a substitui: ele é o que você deixa aberto do lado enquanto faz.
> **v1.0 · 20/09/2026** · escrito para a SPEC EXTRA-001.10.

---

## 🔴 ANTES DE MAIS NADA: isto é de verdade

**Abrir um atendimento no portal aciona uma loja ou um prestador de verdade.** Não existe "modo teste".

```
✅ SÓ capture quando houver DEMANDA REAL de um segurado — um acionamento que você faria de qualquer jeito
   (é a decisão D-PILOTO-05 do Founder)
⛔ NUNCA invente um acionamento só para capturar
⛔ NUNCA use a apólice de um cliente sem que ele tenha pedido o serviço
```

Se por qualquer motivo você precisar interromper depois que o número do atendimento já apareceu:
**cancele pelo próprio portal**, na hora, do jeito que a corretora já faz. Um pedido aberto e esquecido vira serviço
agendado no nome de um segurado que não pediu.

**Em uma frase:** *você já faz o acionamento todo dia. A única coisa nova é abrir o F12 antes de começar, salvar
algumas telas, e no fim exportar um arquivo.*

---

## 1. ANTES de abrir o site (2 minutos — e é a parte que mais se erra)

A ordem importa. Se abrir o portal primeiro, o gravador perde o começo e a captura não serve.

```
1. Abra uma JANELA ANÔNIMA do navegador          Ctrl + Shift + N
   (por quê: sem cookies antigos, a gravação fica limpa e não mistura sessões de outro dia)

2. Aperte F12                                     abre o painel do desenvolvedor
3. Clique na aba  Network  (ou "Rede")
4. ✅ marque  Preserve log    ("Preservar registro")
5. ✅ marque  Disable cache   ("Desabilitar cache")
   (por quê: sem estas duas, tudo some quando a página troca — e é justamente a troca de tela que interessa)

6. Ligue a gravação de tela:  Win + G  →  botão de gravar
   (por quê: o vídeo mostra ONDE você clicou; o arquivo do navegador mostra o que foi enviado. Os dois juntos
    explicam a tela; um só, não)

7. SÓ AGORA digite o endereço do portal
```

⚠️ **Não feche o painel do F12 em nenhum momento.** Se ele atrapalhar, arraste a borda para deixá-lo fino, ou use
os três pontinhos `⋮` → *Dock side* → embaixo.

---

## 2. DURANTE — três coisas, e só três

### a) Fale em voz alta o **porquê** de cada escolha
A gravação está ligada. Diga o que estiver pensando:

> *"escolhi VIDRO DE PORTA e não VIDRO DE JANELA porque o dele sobe e desce"*
> *"marquei que é maior que uma moeda de 1 real porque a trinca passa de um palmo"*
> *"esta loja eu escolhi porque é a mais perto do trabalho dele, não a mais perto de casa"*

É isso que ensina o robô a **decidir**. A tela sozinha só ensina a **preencher**.

### b) Pare **3 segundos** em cada tela — e mais nas três que nunca vimos
Três segundos parado é o que garante que tudo terminou de carregar antes de você clicar.

🔴 **As três telas que nunca capturamos. Nestas, pare, respire, e tire print:**

```
1. A tela do Nº DO ATENDIMENTO com a LISTA DE LOJAS (99 %)
   → print da lista inteira, com endereço e distância aparecendo
2. A GRADE DE AGENDAMENTO
   → print do calendário com os dias disponíveis
   → print dos HORÁRIOS de um dia (este é o mais importante de todos: nunca vimos um horário de verdade)
   → print da janelinha "Confirmar agendamento", ANTES de confirmar
   → print da tela que aparece DEPOIS de confirmar
3. O ANEXO DE FOTOS / VISTORIA
   → print do aviso de vistoria, da janelinha de fotos, e da tela com a vistoria já finalizada
```

### c) Deixe o **link de vistoria** legível
Se aparecer um link de vistoria (aquele que você costuma copiar e colar para o segurado), dê um print com ele
**inteiro e legível na tela**, sem cortar. É por ali que o robô vai aprender a gerar o link sozinho.

**E a regra de ouro:** **não cancele, não desista e não feche a aba antes de a última tela terminar de carregar.**
Uma captura que para no meio ensina metade.

---

## 3. DEPOIS — três arquivos, e acabou

### a) O arquivo mais importante: o HAR
```
No painel do F12, aba Network:
  botão direito em qualquer linha  →  "Save all as HAR with content"
                                       ("Salvar tudo como HAR com conteúdo")
```
🔴 **Tem de ser "with content".** Sem isso o arquivo vem vazio por dentro e não serve para nada.
**Como saber que deu certo:** o arquivo fica **grande — de 10 a 30 MB**. Um HAR de 200 KB foi salvo sem conteúdo;
refaça (ou, se a captura já acabou, avise que ficou sem).

### b) O HTML das telas-chave
Em cada tela importante: **Ctrl + S** → tipo **"Página da Web, completa"**.
Fica um arquivo `.html` e uma pasta `_files` do lado — **guarde os dois juntos**.

Telas-chave: passo 3 (com a lista de peças **aberta**), 80 %, 99 % com as lojas, a grade de horários, a tela final.

### c) Onde depositar — **use o mesmo padrão de pasta que já existe**

Hoje o acervo está assim:

```
docs/intake/materiais/portal-vidros/
    YELUM/
        YELUM 1/                      ← lataria, 09/09
        YELUM VIDROS ANTIGO/          ← vidro de porta, 15/08
    PORTO/
```

Então a captura nova vira, por exemplo:

```
docs/intake/materiais/portal-vidros/
    YELUM/
        PARA-BRISA 1/                 ← crie esta, com o nome da peça e um número
            abraseuatendimento.com.br.har
            3 QUAL VIDRO Atendimento Web.html    +  a pasta  _files  do lado
            5 LOJAS 99 Atendimento Web.html      +  _files
            GRADE DE HORARIOS.png
            CONFIRMAR AGENDAMENTO.png
            TELA FINAL.png
            gravacao.mp4
            notas.txt
```

Nome de arquivo: **um número na frente, na ordem em que a tela apareceu**, e o resto em português mesmo.

### d) O `notas.txt` — três linhas, escritas na hora

```
Seguradora: Yelum   Peça: para-brisa   Data: 20/09/2026
O que aconteceu: fui até o agendamento e confirmei loja + dia + hora. Escolhi a loja X porque era a mais perto
do trabalho dele.
O que deu errado / estranho: a grade do dia 22 apareceu vazia; usei o dia 23.
```

Escreva **na hora**. Em dois dias ninguém lembra por que escolheu aquela loja — e é essa frase que vale mais do que
o arquivo de 30 MB.

---

## 4. O que NUNCA fazer

```
⛔ NUNCA use a senha do PORTAL DE CORRETOR nesta captura. É o portal de vidros do segurado, e só ele.
   Se por engano você entrar logada em algum lugar, AVISE — o arquivo guarda o crachá de entrada
⛔ NUNCA dois clientes na mesma captura. Um acionamento = uma pasta. Misturar dois embaralha tudo e o material
   fica inútil
⛔ NUNCA commite, suba no Git, mande por e-mail ou cole em chat qualquer arquivo dessa pasta.
   Ela tem CPF, placa, nome, telefone e o crachá de entrada do navegador. Ela fica NA MÁQUINA, na pasta de intake,
   e ninguém a versiona
⛔ NUNCA edite o HAR "para tirar os dados". Quem lê sabe mascarar; um HAR editado à mão deixa de bater e perde o
   valor
⛔ NUNCA refaça um acionamento que já nasceu, "para capturar melhor". Seriam dois pedidos no nome do mesmo segurado
```

---

## 5. E se não aparecer nenhum para-brisa nos próximos dias?

**Está tudo bem. A SPEC não para.** O que ela fecha sem nenhuma captura nova:

```
✅ Lataria / martelinho na Yelum, do WhatsApp até o comprovante, sem ninguém no portal
✅ O robô passa a gravar peça, causa e cidade no portal (hoje ele simplesmente não grava)
✅ Cadastro de solicitante e de corretor, que hoje faltam e são obrigatórios
✅ O mapa certo das 38 seguradoras do portal (hoje são 3 no código, e uma delas nem existe lá)
✅ O agente passa a perguntar a CIDADE onde o serviço vai acontecer — hoje ele usa o endereço de casa, que
   frequentemente está errado
✅ As perguntas de retrovisor, farol, lanterna e para-choque, tiradas da lista da própria apólice
✅ O robô passa a MOSTRAR ao segurado as lojas, as distâncias, os dias e os horários (sem clicar)
✅ Tela que o robô não conhece deixa de virar silêncio: vira um aviso com o resumo do caso para uma pessoa assumir
✅ O freio de segurança por acionamento, que hoje é geral
```

E o que fica **escrito, testado e desligado**, esperando a captura:

```
🟡 o clique que CONFIRMA loja, dia e hora
🟡 as perguntas próprias do para-brisa (sensor de chuva, faixa degradê, ADAS)
🟡 o serviço a domicílio
🟡 o anexo de fotos e o link de vistoria gerado pelo robô
```

**Então a ordem é simples:** a SPEC roda agora com lataria. A captura entra quando a vida trouxer um para-brisa de
verdade — e aí uma SPEC pequena liga o que já está pronto.

---

## 6. Se qualquer coisa der errado no meio

```
o F12 fechou sem querer          → reabra, remarque Preserve log, e ANOTE no notas.txt em que tela isso aconteceu
a página travou                  → NÃO recarregue às cegas. Tire print da tela travada primeiro (ela é dado)
você cancelou o atendimento      → ótimo: capture a tela de cancelado também. Ela também nunca foi bem medida
o HAR ficou pequeno demais       → foi salvo sem conteúdo. Se a captura já acabou, anote no notas.txt; não dá para
                                   recuperar depois
esqueceu de gravar a tela        → o HAR sozinho já ajuda muito. Só escreva no notas.txt o porquê de cada escolha,
                                   com mais detalhe que o normal
```

---

*Autoridades: D-PILOTO-05 (nenhum acionamento sem demanda real) · D-PILOTO-17 (Bradesco: captura antes de código) ·
`DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §10.6 (a lista das 12 capturas) ·
`docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md` (a versão tela por tela).*
