# Plano de execução — SPECs 063 a 069

> **31/07/2026.** Substitui o rascunho de ontem. Escrito depois de seis
> auditorias com prova e da análise de 46 telas do InfoCap.
> **Não é SPEC.** Cada uma será escrita em detalhe, uma a uma.
>
> Nota 0–100 = valor percebido pelo corretor, ou aumento de capacidade nossa.

---

# PARTE I — O QUE SABEMOS AGORA E NÃO SABÍAMOS ONTEM

## 1. Os números reais da Resulta

Extraídos das telas do próprio sistema dela:

```
prêmio 2024 ............ R$ 24.261.000
comissão 2024 .......... R$  3.637.000
clientes cadastrados ...      14.540
documentos/ano .........       4.400        comissão média R$ 826/doc
```

**E a queda que ninguém decompôs:** documentos caíram **46,7%** e negócios novos
**82,4%** contra o ano anterior. O painel mostra em três telas e **nunca diz de
quem, de qual seguradora, de qual ramo.**

## 2. As três coisas que valem dinheiro imediato

**Duas seguradoras comem a comissão dela.**

```
Sompo ....... 19,4% do prêmio → 25,5% da comissão   (índice 1,31)
Bradesco ..... 9,6% do prêmio →  3,4% da comissão   (índice 0,35)
Mapfre ....... 9,2% do prêmio →  2,2% da comissão   (índice 0,24)
```

Bradesco e Mapfre são **18,8% do que ela entrega e 5,6% do que recebe.** As duas
pizzas estão **lado a lado na mesma tela** e ninguém divide uma pela outra.

**Renovação paga 27% mais que venda nova.** 19,7% contra 15,5%. E ela está com
-82,4% em novos. **Um ponto de retenção vale R$ 14.960/ano.**

**R$ 469 mil/ano endereçáveis** — 12,9% da comissão anual, sem vender uma
apólice nova.

## 3. A armadilha que teria feito nossos números nascerem errados

Existem parcelas com **data de quitação preenchida e valor R$ 0,00**.

> Não foram pagas. **Foram baixadas no cancelamento.**
> Qualquer sistema que conte "quitadas" acerta o campo e erra o fato.

**É pré-requisito de tudo que envolve inadimplência e comissão a receber.**

## 4. A lição de desenho mais importante

Todos os cards de meta do InfoCap, em todos os períodos, mostram
**"0% ATINGIDA — MUITO ABAIXO DA META"**. A meta nunca foi cadastrada.

> **Um alerta que está sempre vermelho não é lido por ninguém.**

É assim que nossos achados morrem se errarmos a dosagem.

## 5. O que o InfoCap já faz — e não vamos refazer

**35 relatórios prontos**, com filtros por período, seguradora, ramo, produtor,
canal. Exporta Excel, PDF e e-mail. Dashboard com ranking e comparativo anual.
Importação de comissão da seguradora. Rateio por produtor com papel e
percentual.

> **A lacuna não é falta de relatório. É que tudo é PULL.**
> Todo relatório espera alguém lembrar de rodá-lo. **Nenhuma tela dispara ação,
> atribui responsável ou cobra prazo.** E o CRM que existiria para isso está
> vazio: zero registros.

**É exatamente o buraco do AutoBrokers: eles têm o dado. Falta o empurrão.**

## 6. As duas corretoras são opostas

```
Resulta ...... empresarial e condomínio · AUTO é só 3,8%
AutoFleet .... 100% auto
```

**Uma análise calibrada numa não serve na outra.** Vira regra: toda análise
nasce com o perfil da corretora como parâmetro.

---

# PARTE II — AS DECISÕES DE ARQUITETURA

Estas são as respostas às perguntas que ficaram abertas. Cada uma vira regra
escrita, não convenção.

## D1 · Auxiliar é nomeado pelo que o corretor GANHA

Testei três formas de organizar:

```
por setor (marketing, contábil, vendas) ......... 35
   é o organograma dele, não o desejo dele
   e cobrança é operacional, financeiro E relacionamento ao mesmo tempo

um auxiliar só que faz tudo ..................... 45
   não dá para desligar uma parte
   vira caixa-preta: ele não sabe o que está ligado

por desejo — o que ele quer que aconteça ........ 92
   ele lê e sabe se quer, sem entender o sistema
   cada um liga, desliga e se paga sozinho
```

> **Ninguém quer "análise de sinistralidade por seguradora".**
> **Todo mundo quer poder de mesa na negociação.**

## D2 · As quatro palavras, com um teste cada

| Termo | Uma linha | Como saber |
|---|---|---|
| **Skill** | *como* se faz | se dois trabalhadores diferentes podem usar |
| **Rotina** | *quando* acontece | se cabe em "toda terça às 8h" |
| **Auxiliar** | *quem* faz | se aparece em "o que trabalha para mim" |
| **Artifact** | *o que* foi entregue | se o corretor abre, guarda ou manda ao cliente |

> **Auxiliar TEM Rotina. Auxiliar NÃO É Rotina.** Hoje o produto inverteu isso.

## D3 · Uma rotina pode aparecer em dois auxiliares

Cobrança recupera comissão presa **e** devolve tempo. Aparece nos dois lugares,
**é a mesma rotina**, roda uma vez. Categoria é etiqueta, não pasta.

## D4 · O que o agente lê e o que o corretor lê são campos diferentes

> **A tela do corretor nunca mostra instrução de agente.**
> **A instrução de agente nunca tem copy de venda.**

Dois campos, dois autores, no mesmo registro. Hoje está misturado — é parte da
bagunça.

## D5 · Um cérebro, seis caras

Motor único de detecção (senão o mesmo cliente vira seis mensagens no mesmo
dia), com auxiliares que são **filtros por domínio**, não motores.

Se alguém propuser tabela por auxiliar, **é motor paralelo com outro nome.**

## D6 · Tudo visível, tudo desligado

**Nenhum auxiliar ou rotina escondido.** Os que não existem aparecem com
etiqueta **EM BREVE** e a descrição já escrita. **Nenhum nasce ligado.**

## D7 · Canais, nesta fase

```
atendimento ........ Evolution Go · número da corretora
cobrança ........... Evolution Go · SEGUNDO número, separado
relatório .......... dashboard + e-mail  (sai do WhatsApp)
META oficial ....... card existe, marcado "em breve" — SPEC-069
```

## D8 · O governador de envio é obrigatório desde já

Hoje **não existe limite nenhum**. A cobrança percorre até 50 destinatários
**sem pausa**, mandando duas mensagens cada — **100 mensagens em rajada.**

## D9 · O chat principal chama qualquer auxiliar

O corretor pede no chat e recebe **ali mesmo, na hora** — em vez de esperar a
rotina. Mesmo motor, resposta síncrona.

## D10 · Conselho tributário: sim, e entregando feito

Não damos a informação — **entregamos o relatório pronto para o contador.**
Com disclaimer, e com a conta feita.

---

# PARTE III — AS SPECS

---

## SPEC-063 · Atendimento e canais que podem ser ligados

**Nota 100.** Sem ela, ligar o agente é incidente, não lançamento.

### Bloco A — Os doze bloqueios

| # | Bloqueio | Grau |
|---|---|---|
| B1 | **agente errado responde o segurado** — `agent_id` nulo faz o sistema escolher o agente ativo mais antigo, que é o copiloto interno, cujo prompt manda entregar CPF sem mascarar | **P0** |
| B2 | ternário morto `None if purpose=="observer" else None` zera `agent_id` ao re-parear | P0 |
| B3 | `request_human_agent` não anexada — `tools_config` vazio nos 3 agentes. **O agente promete humano e não chama** | P0 |
| B4 | handoff só faz UPDATE no banco. **Ninguém é avisado** | P0 |
| B5 | a tela grava em `human_support_destinations`, o backend lê `acionamento_profile`. **A Amandus já está quebrada** | P0 |
| B8 | buffer sem tenant na chave — mesmo cliente em duas corretoras mistura mensagens | **P0 cross-tenant** |
| B6 | `ATTENDANT_INBOUND_ALLOWLIST` pode calar o agente em silêncio | P1 |
| B7 | confirmar imagem corrigida do Evolution Go antes de parear | P1 |
| B9 | `time.sleep` bloqueante trava o processo por ~2s a cada resposta | P1 |
| B10 | Resulta e AutoFleet dividem o mesmo grupo de suporte humano | P1 |
| B11 | cobrança pode sair pelo número do observador — o celular espelhado | P1 |
| B12 | corretora sem agente provisionado responde por omissão | P1 |

### Bloco B — O governador de envio

**A peça que não existe e é obrigatória.**

```
intervalo entre destinatários ..... 30 a 90 segundos, ALEATÓRIO
                                    (intervalo fixo é assinatura de robô)
por hora .......................... teto configurável, padrão 30
por dia, número novo .............. 20 mensagens frias
por dia, número maduro ............ 200
janela .......................... 08:00–20:00, nunca domingo
fila ............................. persistente, retomável, com prioridade
```

**Regra dura:** mensagem fria (para quem não escreveu antes) passa pelo
governador. Resposta dentro de conversa aberta, não.

**E o registro:** toda saída grava quem, quando, por qual número, com qual
intervalo. Sem isso não dá para investigar um bloqueio depois.

### Bloco C — O segundo número

O card de pareamento da corretora ganha **três posições**:

```
[ conectado  ] WhatsApp de Atendimento      o segurado escreve aqui
[ conectar   ] WhatsApp de Cobrança         nós escrevemos daqui
[ em breve   ] WhatsApp Oficial (Meta)      SPEC-069
```

E a guarda que falta: **`observer` nunca pode ser canal de saída.** Hoje ele
recebe a prioridade mais baixa e **ainda assim é usado se for a única ativa** —
é assim que a cobrança sairia pelo celular espelhado do corretor.

### Bloco D — Os corredores

**Mantemos.** A auditoria provou que não competem com o RAG:

```
RAG (8.916 cartas) ..... conversa do agente com o SEGURADO
corredor ............... conversa do motor com a URA DA SEGURADORA
```

Sem corredor não há navegação de menu, não há protocolo verificado, e **não há
modo de teste** — o primeiro teste abriria guincho de verdade.

**O que entra:** um documento de instruções para quem for criar corredor novo —
pré-requisitos, âncoras obrigatórias, política de tela desconhecida, como testar
sem acionar. **Padrão escrito, para a LLM seguinte não inventar.**

### Bloco E — O desperdício encontrado

Os **16 playbooks de conduta**, destilados de atendimento humano, com portão
anti-regressão e otimizador semanal, **nunca chegam ao prompt do atendente.**
Máquina de qualidade sem consumidor.

### Bloco F — Cobrança e atendimento no mesmo WhatsApp

**O buraco:** o cliente recebe o boleto, responde *"já paguei"* — e o atendente
recebe a mensagem crua, sem saber que houve cobrança.

A corrente existe inteira e está partida num elo: a cobrança grava numa tabela
e a nota de contexto lê outra. **E não existe nenhuma skill de cobrança** —
nem 2ª via, nem prazo, nem "já paguei", nem negociação.

### Quando entregar

O agente pode ser ligado sem risco de vazamento e sem promessa falsa. Handoff
notifica. Cobrança sai pelo número certo, espaçada. Quem responde ao boleto sabe
que houve boleto.

---

## SPEC-064 · A ontologia e a casa limpa

**Nota 98.** Não entrega dinheiro direto — **mas toda SPEC seguinte aterrissa
aqui.** Construir o descobridor antes disso cria mais uma página órfã.

### Bloco A — O menu, de 7 pilares para 5

```
AutoBrokers      o chat
Atendimentos     as conversas
Auxiliares       TUDO que trabalha por você
Entregas         tudo que foi feito, com link e histórico
Personalização   quem você é, seus dados, suas conexões
```

**Briefing e Pesquisas saem do menu.** Briefing vira Auxiliar; Pesquisa vira
Skill do chat, com o resultado em Entregas.

### Bloco B — As seis categorias

Nomeadas pelo que o corretor ganha:

```
💰 DINHEIRO QUE VOLTA      o que é seu e está parado
📈 DINHEIRO QUE ENTRA      receita que existe e ninguém foi buscar
🤝 CLIENTE QUE FICA        a renovação antes de virar perda
⚖️ PODER DE MESA           o argumento que você não tem hoje
🛡️ ESCUDO                  o que não custa hoje e custa se acontecer
⏱️ TEMPO QUE SOBRA         a hora que volta pra você
```

### Bloco C — O catálogo de auxiliares

**Todos visíveis. Todos desligados. Os que não existem, com etiqueta EM BREVE e
a descrição já escrita.**

| Auxiliar | Categoria | Estado | O que faz |
|---|---|---|---|
| **O Cobrador** | Tempo · Dinheiro que volta | **existe, renomear** | busca inadimplente no portal, manda boleto, responde dúvida |
| **O Vigia da Manhã** | (todas) | **existe como "Briefing"** | o que precisa de você hoje, num lugar só |
| **O Conferente** | Dinheiro que volta | EM BREVE | confere extrato de comissão contra o esperado, apólice por apólice |
| **O Caça-Comissão** | Dinheiro que volta | EM BREVE | acha comissão recebida que não casou com apólice |
| **O Contador Sombra** | Dinheiro que volta | EM BREVE | anexo errado, fator R, retenção não compensada — com o relatório pronto |
| **O Perdido Achado** | Dinheiro que entra | EM BREVE | quem foi cliente por anos e hoje não tem nada |
| **O Faro Novo** | Dinheiro que entra | EM BREVE | cliente que abriu CNPJ, sócio sem produto pessoal, gap de ramo |
| **O Resgate** | Dinheiro que entra | EM BREVE | cotação que esfriou, ex-cliente na janela de revanche |
| **O Guardião da Renovação** | Cliente que fica | EM BREVE | o aumento que ele não vai aceitar, a renovação órfã, o sinistro apodrecendo |
| **O Mesa-Redonda** | Poder de mesa | EM BREVE | sinistralidade da seguradora, sua carteira vs a média dela, onde você perde cotação |
| **O Escudeiro** | Escudo | EM BREVE | uso não declarado, FIPE errado, apólice sem vistoria, registro vencendo |
| **O Faxineiro** | Tempo que sobra | EM BREVE | contato inválido, cadastro duplicado, apólice parada na entrega |
| **O Radar** | Poder de mesa | **existe, invisível** | mudança de regulação e de condição geral |

**O que morre:** os 3 templates de teste, as 3 instalações sujas, a rotina da
Globo, e o caminho de auxiliar do Blueprint Center — que só produziu lixo.

### Bloco D — A entrega

Hoje `delivery_status` é `pending` em **20 de 20** publicações, e a função que
decide o canal **não é chamada por ninguém**.

```
dashboard ...... sempre, é o registro
e-mail ......... relatório e achado — sai do WhatsApp
WhatsApp ....... só a manchete de uma linha, com link
push ........... complemento, nunca substituto
```

**E a página Entregas** — tudo que foi feito, por qual auxiliar, quando, com o
link do artefato. Hoje `/dashboard/atividades` existe e é fraca.

### Bloco E — Personalização por corretora

**Hoje não existe.** Não há como escrever a configuração do auxiliar depois da
instalação — embora o lado da leitura já espere por ela.

> Quando o corretor pedir um ajuste, o auxiliar pergunta **"é sempre assim?"** e
> grava **só para ele**. Nunca no global.

**E o chat principal edita** — liga, desliga, muda horário, muda canal, ajusta o
que o auxiliar entrega.

### Bloco F — A casa limpa

**Documentação.** README desatualizado, SPECs que se contradizem, legado que
confunde toda LLM nova. **Nomenclatura única, escrita uma vez.**

**Portal admin.** Hoje o submenu "Inteligência" tem 9 itens, **4 dos quais
respondem alguma variação de "o que o sistema pode fazer"**. Precisa de um lugar
só para Skills, um para Ferramentas e MCPs, um para Conectores.

**O P1 de segurança:** a verificação do cookie de admin **só checa que ele
existe** — sem validar assinatura nem expiração. E ela guarda criar template e
instalar em qualquer corretora.

**Três tabelas** com colunas na tela e zero linhas no banco: ou implementa, ou
apaga.

### Quando entregar

Você e qualquer LLM dizem, sem hesitar, o que é cada coisa e onde mora.
**Auxiliar novo nasce visível.** O corretor liga o que quiser, no canal que
quiser, e vê tudo que foi feito por ele num lugar só.

---

## SPEC-065 · A carteira e o dinheiro visível

**Nota 99.** É a primeira que o corretor sente no bolso.

### Bloco A — A leitura agregada

**O que já está liberado e nunca foi chamado:**

```
/cotacoes ......... o funil comercial inteiro, numa chamada
/atendimentos ..... 2.355 registros na Resulta
/seguradoras ...... 61 companhias — decodifica ALLI → Allianz
/ramos ............ 50 ramos
```

**E testar `/producao`** com período em vez de CPF — deu 500 uma vez porque foi
chamado errado. **Se responder, a leitura agregada colapsa numa chamada.**

**Trabalhar como se tudo estivesse liberado** — a liberação vem na semana que
vem e o código estará pronto.

### Bloco B — A carteira local

Não existe tabela de apólice. Sem espelho não há "quantas vencem em setembro".

**E a regra que salva os números:** parcela com data de quitação e valor zero
**não foi paga** — foi baixada no cancelamento. Entra como teste, não como
comentário.

### Bloco C — Parar de jogar a comissão fora

O robô da Allianz **já lê** valor de comissão e data prevista de cancelamento,
parcela por parcela. **O código descarta o campo antes de gravar.**

### Bloco D — Os primeiros detectores que apontam para dinheiro

Hoje os doze detectores vigiam o próprio sistema. Nenhum olha o negócio.

| Detector | A frase |
|---|---|
| comissão presa | *"R$ 2.180 seus não foram gerados; 6 apólices cancelam em 15 dias"* |
| carteira vazando | *"62 apólices venceram sem renovar e sem cancelar: R$ 168 mil"* |
| cobertura suspensa | *"7 clientes sem cobertura — se baterem hoje, a culpa vira sua"* |
| cotação esfriada | *"19 cotações têm o cliente como último a falar"* |
| renovação órfã | *"18 vencem em 30 dias sem ninguém ter falado"* |
| mix que paga | *"Bradesco é 9,6% do seu prêmio e 3,4% da sua comissão"* |
| margem real | *"você recebeu R$ 1.003 e repassou R$ 551 a 5 produtores"* |
| cliente perdido | *"ADAIR foi seu cliente por 6 renovações. Hoje: zero"* |
| cancelamento precoce | *"cancelou 68 dias após a emissão — 7º do mês"* |
| autópsia da queda | *"você caiu 46,7%. A queda está em [quem]"* |

### Quando entregar

O corretor recebe uma lista de dinheiro dele que está parado, com nome, apólice
e valor.

---

## SPEC-066 · O acervo: SUSEP, condições gerais e o RAG definitivo

**Nota 95.** É o que nenhum concorrente pago por seguradora pode copiar.

### Bloco A — As condições gerais, versionadas por vigência

**Verificado à mão:** consulta pública por número de processo SUSEP, sem senha,
devolve **todas as versões com data**. O produto de auto da Allianz mudou
**72 vezes**.

> Vale a versão que estava valendo **no dia em que a apólice foi assinada.**
> Um RAG que indexa só a atual responde errado para apólice em vigor **e não
> percebe.**

**Ingestão dirigida**, nunca varredura: os processos que a corretora vende, mais
os produtos líderes. Milhares, não 510 mil. **Varrer 510 mil PDFs de servidor
público é agressivo** — e é decisão sua, não minha.

### Bloco B — A curadoria pelo plano Max

**O mesmo método que destilou 8.800 conversas por US$ 0,00.**

```
exportar ....... o PDF da condição geral, fatiado por cláusula
destilar ....... subagente lê e escreve as cartas
aplicar ........ script grava, publicador indexa
```

**E o cruzamento que só nós podemos fazer:** confrontar as 8.916 cartas
destiladas de atendimento real **contra a condição geral escrita**. Onde o
atendimento contradiz o contrato, **uma das duas está errada — e vale saber
qual.**

### Bloco C — A sinistralidade

**A coluna documentada pela SUSEP está morta desde 2013.** Quem segue o manual
calcula 0% e não percebe.

```
número ......... TABELA, consultada por SQL — nunca texto no RAG
cláusula ....... RAG, particionado por vigência
identidade ..... AO VIVO
```

Embutir R$ 37 bilhões num pedaço de texto é convidar o modelo a errar aritmética
e citar número velho sem saber.

**Detecção de mudança sem baixar 542 MB:** ler só o sentinela de data por range
request — **6 requisições, 3.398 bytes**. Elimina 3 de cada 4 ingestões.

### Bloco D — As outras fontes

```
ANS ........... reajuste real por contrato — poder de negociação em saúde PME
CNPJ Receita .. prospecção com CNAE, porte, praça e contato
API corretores  166.231 corretores, proxy da Receita por CNPJ, sem chave
ISP-RJ/SSP-SP . risco por município e taxa por 100 mil veículos
FIPE .......... validação de valor  ⚠ decisão sua: eles dizem não ter API
```

### Bloco E — O motor de busca

`miniCOIL` no lugar do BM25 — *franquia*, *prêmio* e *sinistro* são polissêmicos
e o BM25 estatístico não distingue. **Já está dentro do Qdrant que rodamos.**

**E antes de trocar qualquer modelo: o conjunto de perguntas com resposta
certa.** ~200 perguntas reais com a carta que *deveria* aparecer. **Sem isso,
todo upgrade é fé.**

### Quando entregar

O agente responde *"a apólice dele é de fevereiro de 2024, e naquela versão isso
era excluído"*. E o corretor sabe qual seguradora vai apertar antes de apertar.

---

## SPEC-067 · O Descobridor

**Nota 100 de valor, e a mais difícil.** Só funciona sobre as três anteriores.

### Bloco A — Os três anéis

**Anel 1 · o catálogo.** 59 análises escritas, com a frase de saída pronta e a
conta do quanto vale. Determinísticas, baratas. **Entregam ~90% do valor.**

**Anel 2 · as formas.** Seis formas aplicadas sozinhas sobre qualquer campo:

```
divergência ......... duas fontes que deveriam bater e não batem
concentração ........ Pareto em qualquer dimensão
quebra de série ..... o que fugiu da própria tendência
coorte .............. grupo que se comporta diferente
queda de funil ...... perda entre duas etapas
o que ELE DISSE ..... declarou X, o sistema registra Y   ← só nossa
```

**Filtro duro: só sobrevive o que tem valor em R$ calculável.**

**Anel 3 · o mapa de domínios.**

> O modelo não deixou de pensar em Google por burrice. Deixou porque **"presença
> digital" não estava no mapa** — e o site dela não está no banco.

Doze domínios, revisados por gente. **Cada domínio novo enriquece o sistema sem
uma linha de código.**

### Bloco B — O mecanismo que teria achado o Google sozinho

> Quando o corretor age **sem** o sistema ter sugerido — contratou alguém para o
> site, cobrou a seguradora, trocou o vendedor de um cliente — **isso é um
> achado que o sistema perdeu.**
>
> Registrar e perguntar uma vez: *"você fez isso por quê? eu deveria ter te
> avisado?"*

### Bloco C — A taxonomia

"Alerta" é lixeira — em três meses tudo vira alerta. Classificar **pelo que se
espera do corretor**:

```
AGORA ................. perda em curso, executar hoje
DINHEIRO NA MESA ...... valor quantificado, autorizar
OPORTUNIDADE .......... receita nova possível, decidir
EXPOSIÇÃO ............. não custa hoje, custa se acontecer
CONSELHO .............. mudança estrutural, pensar
LIMPO ................. conferido, nada encontrado
```

### Bloco D — A dosagem

```
3 itens no diário · 5 a 7 no semanal · 1 manchete
um item por domínio por vez
ordenar por R$ × probabilidade de ação — não por gravidade
nunca dois achados que exigem a mesma decisão
backlog visível, nunca empurrado
```

**A regra editorial que carrega o produto: uma manchete por semana** — o maior
achado, **já investigado**, com número, evidência e ação pronta.

### Bloco E — O recibo de vigilância

*"Conferi 41 verificações hoje. 38 limpas, 3 pedem atenção."*

**Nunca push, sempre rodapé, sempre auditável** — clicar em "limpa" mostra o que
foi conferido. **É a resposta quando ele perguntar "por que eu pago isso?"**

### Bloco F — A permissão para investigar

**Dois tempos: farejada → investigação.** A farejada roda sempre, com orçamento
fixo, e produz indício com magnitude. A investigação é trabalho durável, com
custo declarado, e passa por aprovação.

O pedido precisa de quatro coisas: **o número · a incerteza honesta · o custo
para ele · o que sai no fim.**

### Bloco G — A copy

```
no WhatsApp, uma linha:
  "Achei ouro na sua contabilidade. R$ 98 mil que você pode não
   estar devendo. Detalhe completo: [link]"

no artefato, a copy inteira:
  "Você paga imposto no anexo errado — e não é culpa sua"
  O que descobri · Quanto vale · Por que ninguém viu ·
  O que fazer segunda · A carta pronta pro seu contador
```

**A manchete vende. O artefato entrega. E no fim tem o trabalho já feito** — não
a instrução de como fazer.

---

## SPEC-068 · Prontidão e go-live

**Nota 88.** É o portão, não a festa.

- **CA-020** — o middleware libera todo `/api/` sem olhar sessão. A proteção
  depende de cada autor lembrar. **Inverter: exigir sessão por omissão**, com
  lista curta e explícita do que é público.
- **O conjunto de perguntas com resposta certa** — se não veio na 066
- **Auditoria final com outros modelos** — GPT Sol, Fable, como você pediu
- **Canário** Resulta → AutoFleet, com número conferido à mão antes de sair
- **Prova de restore, RPO/RTO, OpenTelemetry** — pendências da 062

---

## SPEC-069 · Canais definitivos *(executar depois do piloto)*

**Nota 90 de economia, 0 de urgência.** Você decidiu, e concordo: **implantar
agora atrasaria o piloto.** Com 3 a 5 boletos por dia, o risco atual é baixo.

### Por que vale, quando chegar a hora

```
Meta oficial, utility (boleto) ..... R$ 0,037 por mensagem
resposta dentro da janela 24h ...... GRÁTIS
marketing .......................... R$ 0,34   ← o preço que assusta,
                                                  e não é o nosso caso

500 boletos/mês pela Meta .......... R$ 18
Z-API .............................. R$ 99,99/mês
Zenvia (mesmos 500) ................ R$ 375 + R$ 649 de setup
```

**O caro nunca foi a Meta — são os intermediários.** Zenvia cobra 15× o preço
dela.

### O que entra nesta SPEC

- **Provedor Meta** como o quinto no registro — **o contrato já tem as marcas
  `templates` e `session_window_24h`.** Não é motor paralelo.
- **E-mail definitivo: Amazon SES** — US$ 0,10/mil, faturado em BRL com nota
  fiscal, e **isolamento de reputação por corretora** a US$ 0,005/mês cada.
  Pausa uma sem afetar as outras. Nenhum concorrente oferece isso.
- **Push/PWA** — grátis, complemento, nunca substituto (adesão real ~6%)
- **IP por corretora acima de ~100** — não por reduzir bloqueio, **por conter
  raio de explosão.** Uma que abuse contamina todas.
- **Telegram: não.** 38% de uso diário e caindo, sem processo de apelação.

### Os prazos escondidos

**Cadastro limitado a 10 clientes novos por semana** até passarmos por três
verificações da Meta. Para centenas de corretoras, **começar cedo.**

E a partir de 01/07/2026 dá para faturar em BRL pela Facebook Brasil, com nota
fiscal local e sem IOF. **Migração obrigatória até 30/06/2027.**

### As dependências que ninguém mapeou

- **O vazamento do Evolution Go continua aberto lá em cima.** Quatro correções
  propostas, nenhuma aceita, nenhum commit desde 3 de julho. **`latest` é a
  versão quebrada.** Estamos protegidos porque forkamos — mas cada atualização
  exige reaplicar o patch.
- **Heartbeat de licença** com a fundação Evolution: a API responde 503 até
  ativar. **Dependência de terceiro na frente de toda a camada de WhatsApp.**
- **A licença exige aviso visível** de que o sistema usa Evolution, sob pena de
  licença comercial. **Para produto white-label, é decisão sua.**

### E o que a pesquisa derrubou

**Proxy não reduz bloqueio.** Pesquisadores rodaram a mesma biblioteca de um
único IP fixo, 7.000 números por segundo, durante meses — **nunca bloqueados.**
E um operador com proxy rotativo, VPS separada e aquecimento foi **banido em 40
mensagens.**

**"Aquecimento de chip" não tem evidência.** Os protocolos publicados discordam
entre si em 5 a 10 vezes. **Existe um mercado de R$ 47 a 149/mês construído
sobre premissa que ninguém mediu.**

---

# PARTE IV — A ORDEM

```
063 ── atendimento e canais ....... sem ela, ligar é incidente
064 ── ontologia e casa limpa ..... tudo aterrissa aqui
065 ── carteira e dinheiro ........ primeiro valor no bolso
066 ── acervo e RAG definitivo .... a diferenciação
067 ── o Descobridor .............. a coroa, precisa das três
068 ── prontidão .................. o portão
069 ── canais definitivos ......... depois do piloto
```

**063 e 064 podem ser discutidas em paralelo.** As outras dependem da anterior.

---

# PARTE V — O QUE DEPENDE DE VOCÊ

| # | Decisão | Impacto |
|---|---|---|
| 1 | **O nome do Descobridor** — "achador de ouro" não presta. Proponho **O Descobridor**, e as seis categorias acima | dá identidade ao produto inteiro |
| 2 | **Varredura das condições gerais** — dirigida (recomendo) ou completa | 510 mil PDFs de servidor público |
| 3 | **FIPE** — a API interna funciona, mas eles dizem publicamente que não oferecem | conflito canônico |
| 4 | **Benchmark entre corretoras** — a política de 14/07 diz que o global nunca é acessível por corretora | o dado mais difícil de copiar |
| 5 | **Aviso visível da Evolution** no produto | licença |
| 6 | **Google Business Profile** das corretoras | destrava marketing |
| 7 | **O que a Resulta e a AutoFleet devem ver na segunda** | define onde apertamos |

---

# PARTE VI — O QUE NÃO ESTÁ NO PLANO E DEVERIA ESTAR NO SEU RADAR

**Os áudios.** 3.653 perdidos. A correção está no ar. **A reconexão de segunda é
a única chance** de recuperar os que ainda existirem nos servidores do WhatsApp.

**Os dois `detect_signals` presos em `queued`** desde 28 e 30/07. Ninguém
investigou.

**A AutoFleet não tem conexão InfoCap** — o atendente dela é cego para apólice.

**Os números da AutoFleet parecem incompletos:** julho acumulava R$ 41.996
contra R$ 705.002 no mesmo dia do ano anterior. **Mais provável lançamento
atrasado que colapso** — mas isso, em si, é uma oportunidade de detecção.
