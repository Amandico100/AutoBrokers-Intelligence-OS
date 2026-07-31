# Pré-plano das SPECs — 31/07/2026

> Rascunho para discussão. **Não é SPEC.** Cada uma será escrita em detalhe,
> uma a uma, depois de você opinar. Nota 0–100 = valor percebido pelo corretor
> ou aumento de capacidade nossa.

---

## O que as três auditorias de hoje descobriram

**Nenhuma delas foi opinião. Todas trouxeram prova.**

### 1. O agente errado atenderia o segurado — P0

A integração grava `agent_id = NULL` por causa de um ternário que devolve a
mesma coisa nos dois lados. Sem `agent_id`, o sistema escolhe **o agente ativo
mais antigo** — que na Resulta é o **copiloto interno do corretor**, cujo prompt
manda entregar CPF sem mascarar.

```
Resulta · AutoBrokers (core) ....... 21/06 00:36 · ATIVO
Resulta · Saionara (atendimento) ... 21/06 04:45 · desligado
```

**Parear é seguro. Ligar o agente, hoje, não é.**

### 2. Três sistemas se chamam "Auxiliar", e o menu chama de Auxiliares o que não é

```
menu → "Auxiliares" → /dashboard/auxiliares → mostra ROTINAS
auxiliares de verdade → /dashboard/auxiliares/meus → SEM LINK NO MENU
```

E `Briefing` e `Pesquisas` são **pilares de primeiro nível** — quando os dois
são, por definição, Auxiliares. O próprio `lib/navigation.ts` tem escrito o
princípio *"o menu não cresce"* — e o menu cresceu.

### 3. Os doze detectores vigiam o próprio sistema

Fila parada, aprovação pendente, conexão degradada, Work Run travado.
**Nenhum olha dinheiro, venda, renovação ou cliente.** É por isso que o sistema
nunca acharia o Google: ninguém disse a ele que a corretora tem um negócio.

### 4. O que funciona, e é pouco

```
briefing gerado todo dia ....... 20 publicações · 182 itens · 100% pendentes
rotina de cobrança ............. 32 execuções · desligada desde 15/07
auxiliares ..................... 4 execuções, todas manuais, US$ 0,00037
                                 nenhum roda há 52 dias
pesquisas ...................... 7 skills ativas · ZERO pesquisas
```

---

# A SEQUÊNCIA

Seis SPECs, em linha reta. Cada uma deixa o sistema utilizável num degrau a
mais — não são camadas que só valem no fim.

---

## SPEC-063 · Atendimento que pode ser ligado

**Nota 100.** Sem ela, ligar o agente é incidente, não lançamento.

### O que resolve

| # | Bloqueio | Gravidade |
|---|---|---|
| B1 | agente errado responde o segurado (prompt interno, CPF sem máscara) | **P0** |
| B2 | ternário morto zera `agent_id` ao re-parear | P0 |
| B3 | `request_human_agent` não anexada — o agente promete humano e não chama | P0 |
| B4 | handoff só faz UPDATE no banco — **ninguém é avisado** | P0 |
| B5 | a tela grava em `human_support_destinations`, o backend lê `acionamento_profile` | P0 |
| B6 | `ATTENDANT_INBOUND_ALLOWLIST` pode calar o agente em silêncio | P1 |
| B7 | confirmar imagem corrigida do Evolution Go antes de parear | P1 |
| B8 | buffer sem tenant na chave — mensagens de duas corretoras se misturam | **P0 cross-tenant** |
| B9 | `time.sleep` bloqueante trava o processo inteiro por 2s a cada resposta | P1 |
| B10 | Resulta e AutoFleet dividem o mesmo grupo de suporte humano | P1 |
| B11 | cobrança pode sair pelo número do observador (celular espelhado) | P1 |
| B12 | corretora sem agente provisionado responde por omissão | P1 |

### Decisões que preciso de você

**Corredores: mantemos.** A auditoria provou que não competem com o RAG —
o RAG conversa com o **segurado**, o corredor conversa com a **URA da
seguradora**. Sem corredor não há acionamento, não há protocolo verificado e
não há modo de teste (o primeiro teste abriria guincho de verdade).

**Mas achei o desperdício real:** os 16 **playbooks de conduta**, destilados de
atendimento humano, com portão anti-regressão e otimizador semanal, **nunca
chegam ao prompt do atendente**. Máquina de qualidade sem consumidor. Isso entra
nesta SPEC.

### Quando entregar

O agente de atendimento pode ser ligado na Resulta e na AutoFleet **sem risco de
vazamento e sem promessa falsa**. Handoff notifica de verdade. Cobrança não sai
pelo celular espelhado.

---

## SPEC-064 · A ontologia: Auxiliar, Rotina, Skill, Artifact

**Nota 95.** Não entrega dinheiro direto — mas **toda SPEC seguinte aterrissa
aqui**. Construir o achador de ouro antes disso cria mais uma página órfã.

### As quatro palavras, com um teste cada

| Termo | Uma linha | Como saber |
|---|---|---|
| **Skill** | *como* se faz | se dois trabalhadores diferentes podem usar, é Skill |
| **Rotina** | *quando* acontece | se cabe em "toda terça às 8h", é Rotina |
| **Auxiliar** | *quem* faz | se aparece em "o que trabalha para mim", é Auxiliar |
| **Artifact** | *o que* foi entregue | se o corretor abre, guarda ou manda ao cliente |

> **A regra que desfaz a confusão: Auxiliar TEM Rotina. Auxiliar NÃO É Rotina.**
> Hoje o produto inverteu isso.

### O menu que resulta — de 7 pilares para 5

```
AutoBrokers (chat)
Atendimentos
Auxiliares      ← Briefing, Radar, Cobrança, Resumo: TODOS aqui,
                  cada um com sua página, agenda e histórico
Memórias
Personalização
```

**Briefing vira Auxiliar de plataforma**, instalado por padrão. Ele já tem tudo:
agenda, perfil por empresa, execução durável, saída. Falta só reconhecê-lo.

**Pesquisa vira Skill**, não página. Já existem 7 skills de pesquisa ativas.
Nasce no chat; o resultado se reencontra no histórico de trabalhos. **Monitor**
de pesquisa, esse sim, é Auxiliar.

### O que também entra

**A entrega.** Hoje `delivery_status` é `pending` em 20 de 20 publicações e a
função que decide o canal **não é chamada por ninguém**. Canais: dashboard,
WhatsApp, e-mail. E uma página onde tudo que foi entregue fica guardado.

**Personalização por corretora.** Hoje **não existe** — não há como escrever
`tenant_auxiliaries.config` depois da instalação. O lado da leitura já espera
por isso. Quando o corretor pedir um ajuste, o auxiliar pergunta *"é sempre
assim?"* e grava **só para ele**, nunca no global.

**A limpeza.** Morrem: 3 templates de teste, 3 instalações sujas, a rotina da
Globo, o caminho de auxiliar do Blueprint Center, e três tabelas que têm colunas
na tela e zero linhas no banco.

**Um P1 de segurança:** `hasAdminCookie()` só verifica que o cookie **existe** —
sem validar assinatura nem expiração. E ele guarda criar template e instalar em
qualquer corretora.

### Quando entregar

Você e qualquer LLM conseguem dizer, sem hesitar, o que é cada coisa e onde ela
mora. **Auxiliar novo nasce visível.** O corretor recebe o que foi feito por ele,
no canal que ele escolheu.

---

## SPEC-065 · A carteira e o dinheiro visível

**Nota 98.** É a primeira que o corretor sente no bolso.

### O que entra

**A leitura agregada da carteira.** Hoje a InfoCap só responde por CPF. Sem
agregado não há "quantas vencem em setembro" nem "quanto de comissão está preso".

**Primeiro o que já está liberado e nunca foi chamado:**

```
/cotacoes ......... o funil comercial inteiro, numa chamada
/atendimentos ..... 2.355 registros na Resulta
/seguradoras ...... 61 companhias (decodifica ALLI → Allianz)
/ramos ............ 50 ramos
```

**E testar `/producao`** com os parâmetros certos — deu erro 500 uma vez porque
foi chamado com CPF em vez de período. Se responder, a leitura agregada colapsa
numa chamada só.

**Parar de jogar a comissão fora.** O robô da Allianz **já lê** valor de comissão
e data prevista de cancelamento, parcela por parcela — e o código descarta o
campo antes de gravar.

**Os primeiros detectores que apontam para dinheiro.** Hoje os oito caminhos de
recomendação falam todos da saúde do próprio sistema. Estes falam do bolso:

| Detector | Frase que aparece |
|---|---|
| comissão presa | *"R$ 2.180 seus não foram gerados; 6 apólices cancelam em 15 dias"* |
| carteira vazando | *"62 apólices venceram sem renovar e sem cancelar: R$ 168 mil"* |
| cobertura suspensa | *"7 clientes sem cobertura por falta de pagamento — se baterem hoje, a culpa vira sua"* |
| cotação esfriada | *"19 cotações têm o cliente como último a falar. Silêncio é seu, não dele"* |
| renovação órfã | *"18 vencem em 30 dias sem ninguém ter falado com o cliente"* |

### Quando entregar

O corretor recebe, toda semana, **uma lista de dinheiro dele que está parado** —
com nome, número de apólice e o quanto vale.

---

## SPEC-066 · O acervo externo

**Nota 92.** É o que nenhum concorrente pago por seguradora pode copiar.

### As condições gerais, versionadas por vigência

**Verificado à mão:** consulta pública por número de processo SUSEP, sem senha,
devolve **todas as versões com data**. O produto de auto da Allianz mudou
**72 vezes**.

> Vale a versão que estava valendo **no dia em que a apólice foi assinada**.
> Um RAG que indexa só a atual responde errado para apólice em vigor.

**Ingestão dirigida**, nunca varredura: os processos que a corretora vende, mais
os produtos líderes. Milhares, não 510 mil.

### A sinistralidade por seguradora

**A coluna documentada pela SUSEP está morta desde 2013.** Quem segue o manual
calcula 0% e não percebe. Com a coluna certa:

```
Porto 57,7% · Bradesco 56,1% · Allianz 69,3% · Yelum 71,7%
Amapá 95,1% · São Paulo 67,8% · Amazonas 56,6%
```

### A regra de ingestão

```
número ......... TABELA, consultada por SQL — nunca texto no RAG
cláusula ....... RAG, particionado por vigência
identidade ..... AO VIVO
```

Embutir R$ 37 bilhões num pedaço de texto é convidar o modelo a errar aritmética
e citar número velho sem saber.

### E o motor de busca

`miniCOIL` no lugar do BM25 — *franquia*, *prêmio* e *sinistro* são polissêmicos
e o BM25 estatístico não distingue. **Já está dentro do Qdrant que rodamos.**

### Quando entregar

O agente responde *"a apólice dele é de fevereiro de 2024, e naquela versão isso
era excluído"*. E o corretor sabe qual seguradora vai apertar antes de apertar.

---

## SPEC-067 · O auxiliar que acha ouro

**Nota 100 de valor, e a mais difícil.** Só funciona sobre as três anteriores.

### A resposta à sua pergunta — três anéis

**Anel 1 · o catálogo.** 59 análises escritas, com a frase de saída pronta e a
conta do quanto vale. Determinísticas, baratas. **Entregam ~90% do valor.**

**Anel 2 · as formas.** Seis formas que o sistema aplica sozinho sobre qualquer
campo: divergência · concentração · quebra de série · coorte · queda de funil ·
**o que ele disse × o que o sistema registra**. A última é só nossa — ninguém
mais tem as conversas. **Produz achados que ninguém programou, dentro de formas
explicáveis.** Filtro duro: só sobrevive o que tem valor em R$ calculável.

**Anel 3 · o mapa de domínios.**

> O modelo não deixou de pensar em Google por burrice. Deixou porque **"presença
> digital" não estava no mapa do que é uma corretora** — e o site dela não está
> no banco.

Doze domínios, revisados por gente. **Cada domínio novo enriquece o sistema sem
uma linha de código.**

### E o mecanismo que teria achado o Google sozinho

> Quando o corretor age **sem** o sistema ter sugerido — ele contratou alguém
> para mexer no site, cobrou a seguradora, trocou o vendedor de um cliente —
> **isso é um achado que o sistema perdeu.** Registrar e perguntar uma vez:
> *"você fez isso por quê? eu deveria ter te avisado?"*

### A taxonomia

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

### O recibo de vigilância

*"Conferi 41 verificações hoje. 38 limpas, 3 pedem atenção."*

**Nunca push, sempre rodapé, sempre auditável** — clicar em "limpa" mostra o que
foi conferido. Vale mais em fiscal (onde silêncio gera ansiedade) que em vendas.
**E é a resposta quando ele perguntar "por que eu pago isso?"**

### Um cérebro, cinco caras

Motor único (senão o mesmo cliente vira três mensagens no mesmo dia), com cinco
personas que são **filtros por domínio**, não motores: Carteira · Financeiro ·
Comercial · Risco · Digital.

### O ouro fiscal que apareceu

Corretagem de **seguros** é Anexo III sem fator R, por lei. Mas corretagem de
**plano de saúde, previdência, consórcio e crédito** segue regra diferente —
**sob o mesmo CNAE**. Se a corretora vende os dois e o contador declarou tudo
junto, **é passivo de cinco anos.** Pode valer R$ 98 mil.

**Precisa de decisão sua:** até onde vamos em conselho tributário — disclaimer,
revisão por contador, ou parceria formal?

---

## SPEC-068 · Prontidão

**Nota 85.** É o portão, não a festa.

- **CA-020** — o middleware libera todo `/api/` sem olhar sessão. A proteção
  depende de cada autor lembrar. **Inverter: exigir sessão por omissão.**
- **Conjunto de perguntas com resposta certa** — ~200 perguntas reais de corretor
  com a carta que *deveria* aparecer. **Sem isso, todo upgrade de busca é fé.**
- **Auditoria final** com outros modelos, como você pediu
- **Canário** Resulta → AutoFleet, com número conferido à mão antes de sair

---

# A ORDEM, E POR QUÊ

```
063 ── atendimento seguro ......... sem ela, ligar é incidente
064 ── a ontologia ................ tudo aterrissa aqui
065 ── carteira e dinheiro ........ primeiro valor no bolso
066 ── acervo externo ............. a diferenciação
067 ── o achador de ouro .......... a coroa, precisa das três
068 ── prontidão .................. o portão
```

**063 e 064 podem ser discutidas em paralelo** — não se tocam. As outras
dependem da anterior.

---

# O QUE PRECISO DE VOCÊ

| # | Decisão | Impacto |
|---|---|---|
| 1 | **Colisão de nome:** "Garimpo" já significa minerar a voz do corretor. O achador de ouro precisa de outro nome | a SPEC-067 colide na primeira linha sem isso |
| 2 | **Conselho tributário:** até onde vamos? | é o achado de maior valor e maior responsabilidade |
| 3 | **Benchmark entre corretoras** ("a Porto demora o dobro"): a política de 14/07 diz que o global nunca é acessível por corretora. Agregado derivado não está claramente permitido nem proibido | o dado mais difícil de copiar que existe |
| 4 | **Persona:** cinco analistas nomeados ou um AutoBrokers só com filtro? | tem consequência de preço |
| 5 | **Liberação InfoCap** (comissão, sinistro, endosso, vendedores) | destrava metade da 065 |
| 6 | **Google Business Profile** da corretora | destrava a família de marketing |

---

# AMANHÃ, NA ORDEM

1. **Deploy** — o `/health` ganhou três sinais novos
2. **Conferir** `midia_recuperavel`, `midia_chave_escondida`, `templates_do_briefing`
3. **Conferir** que a imagem corrigida do Evolution Go está no ar
4. **Parear** — é seguro, o observador só captura
5. **NÃO ligar o agente** até a SPEC-063
