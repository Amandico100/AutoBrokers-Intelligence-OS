---
> **Status:** canônica · pronta para execução
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Autoridade superior:** CLAUDE.md · SPEC-052 · SPEC-053 · SPEC-056 · SPEC-057 · SPEC-058
> **Origem:** auditoria de Auxiliares/Rotinas/Briefing/Pesquisa de 31/07/2026
> **Branch:** `feat/spec064-ontologia-casa-limpa`
> **Revoga:** a interpretação da SPEC-019 de que *"Auxiliares = Rotinas"*
---

# SPEC-064 — A Ontologia e a Casa Limpa

> **A frase que resume:** o produto tem três sistemas diferentes se chamando
> "Auxiliar", e o menu do corretor chama de Auxiliares justamente aquele que não
> é. Esta SPEC existe para que **você, o corretor e qualquer LLM** digam, sem
> hesitar, o que é cada coisa e onde ela mora.

---

## 1. Por que esta SPEC existe

O Founder relatou estar confuso. **A auditoria provou que a confusão não é dele
— é do produto.**

### 1.1 A prova, em três linhas

```
menu → "Auxiliares" → /dashboard/auxiliares → mostra ROTINAS
   subtítulo da página: "Rotinas inteligentes que rodam sozinhas"
   card 1: "Rotinas prontas" · card 2: "Minhas rotinas"

auxiliares DE VERDADE → /dashboard/auxiliares/meus → SEM LINK NO MENU
   linkado por 3 arquivos: um de readiness, um de MOCK, e uma página
   que já é inalcançável
```

E `lib/navigation.ts:19` e `:24` colocam **Briefing** e **Pesquisas** como
pilares de primeiro nível — quando os dois são, por definição, Auxiliares.

**A ironia está no mesmo arquivo:** `lib/navigation.ts:40-66` traz um comentário
estabelecendo *"a regra que fica: **o menu não cresce**. Coisa nova entra DENTRO
de um item que já existe."* — e o menu tem 7 pilares, dois dos quais são
Auxiliares que viraram item de menu.

### 1.2 O estado medido

```
auxiliary_templates ........ 6, dos quais 3 são TESTE (50%)
tenant_auxiliaries ......... 5, TODAS da mesma corretora, 3 são lixo (60%)
auxiliary_runs ............. 4, todas manuais, US$ 0,00037 no total
                             nenhum auxiliar roda há 52 dias
routines ................... 2, ambas desligadas, uma é "Notícias da Globo"
auxiliary_requests ......... 0    o funil nunca captou um pedido
capability_gaps ............ 0
auxiliary_events ........... 0
auxiliary_template_releases  0    lido pelo código, nunca escrito
tenant_auxiliary_revisions . 0    ZERO referências em código
briefing_publications ...... 20, delivery_status='pending' em 100%
research_* (10 tabelas) .... 0 em todas · 7 skills ativas, zero pesquisas
```

### 1.3 O que esta SPEC entrega

```
o corretor abre "Auxiliares" e vê TODOS — ativos e disponíveis, numa página só
cada um com nome claro, copy que explica o ganho, e botão de ligar
tudo desligado por padrão; nada roda sem ele mandar
o que foi entregue fica guardado em "Entregas", com link
o corretor pede ajuste e o auxiliar grava SÓ PARA ELE
o chat principal cria, edita, liga e desliga
e nenhuma LLM futura erra onde criar a próxima coisa
```

### 1.4 O que esta SPEC NÃO faz

| Fora do escopo | Onde vai |
|---|---|
| construir os auxiliares novos | um por vez, SPECs próprias |
| carteira, InfoCap, detectores de dinheiro | SPEC-065 |
| SUSEP e condições gerais | SPEC-066 |
| catálogo de análises do Descobridor | SPEC-067 |
| middleware `/api/**` (CA-020) | SPEC-068 |
| e-mail transacional definitivo (SES) | SPEC-069 |

---

## 2. Sobre executar em uma leva

O Founder quer executar tudo de uma vez quando possível. **Concordo, com uma
ressalva registrada.**

```
A · B · C · D    ← UMA COISA SÓ. Não faz sentido separar.
                   São a mesma mudança conceitual vista de quatro ângulos.
                   Executar B sem D deixa o menu certo e a galeria vazia.

E · F · G        ← aditivos. Podem ir juntos ou depois, sem quebrar A-D.

H · I · J        ← limpeza. PODEM ir por último, mas há uma exceção:
                   o P1 de segurança do Bloco I (cookie de admin sem
                   validação) não deve esperar. Ele sai na frente ou junto
                   com A-D.
```

**A ressalva:** A–D mexem em rota, menu e tabela ao mesmo tempo. Se for executado
em uma leva com H (que apaga coisas), **a ordem interna importa**: apagar antes
de a nova estrutura existir deixa o corretor sem tela. **Apagar é sempre o
último passo de qualquer leva.**

---

# BLOCO 0 — A auditoria que vem antes de qualquer linha de código

**Obrigatório. Nenhum bloco desta SPEC começa antes deste terminar.**

Esta SPEC foi escrita a partir de auditorias, prints e leitura de código — não a
partir do sistema rodando com dado real na frente. **Algumas premissas podem
estar erradas**, e é mais barato descobrir agora.

## 0.1 O que a auditoria tem de responder

```
1. CADA AFIRMAÇÃO desta SPEC ainda é verdade hoje?
   arquivo:linha citado ainda existe e diz o que a SPEC diz?
   o número do banco ainda é aquele?

2. O QUE MUDOU desde que a SPEC foi escrita?
   commit novo, migration aplicada, comportamento alterado

3. O QUE A SPEC NÃO PREVIU?
   caminho que ninguém mapeou, dependência escondida,
   efeito colateral em outra parte do sistema

4. O QUE PODE SER MELHOR do que está escrito?
   solução mais simples, peça que já existe e não foi vista,
   ordem de execução melhor

5. O QUE VAI QUEBRAR?
   quem consome o que vamos mudar, e o que acontece com ele
```

## 0.2 O relatório

Entregue ao Founder **antes** da execução, com:

```
✅ CONFIRMADO ....... o que a auditoria verificou e está certo
⚠️ CORRIGIDO ........ o que a SPEC dizia errado, e o certo
➕ ACRESCENTADO ..... o que faltava e precisa entrar
❓ EM ABERTO ........ o que não deu para determinar, e o que falta para saber
🚫 RETIRADO ......... o que a SPEC propõe e a auditoria mostrou não valer
```

**Sem esse relatório aprovado, a execução não começa.**

## 0.3 Por que isso é regra e não zelo

Nesta sessão, seis auditorias mudaram o plano seis vezes — e três acharam
defeitos que teriam ido para produção. **A auditoria não atrasa a execução: ela
evita a reexecução.**

---

# BLOCO A — As quatro palavras

**Este bloco não escreve código de funcionalidade. Escreve a definição que todo o
resto obedece.** É o mais importante da SPEC.

## A.1 As definições

| Termo | Uma linha | O teste para saber |
|---|---|---|
| **Skill** | *como* se faz uma coisa | se **dois trabalhadores diferentes** podem usar, é Skill |
| **Rotina** | *quando* o trabalho acontece | se cabe em **"toda terça às 8h"**, é Rotina |
| **Auxiliar** | *quem* faz o trabalho | se aparece em **"o que trabalha para mim"**, é Auxiliar |
| **Artifact** | *o que* foi entregue | se o corretor **abre, guarda ou manda ao cliente**, é Artifact |

## A.2 A regra que desfaz a confusão

> **Auxiliar TEM Rotina. Auxiliar NÃO É Rotina.**

Hoje o produto inverteu isso: chamou a Rotina de Auxiliar e escondeu o Auxiliar.

**Corolários que valem como regra escrita:**

```
1. Rotina nunca existe sozinha. Toda Rotina pertence a um Auxiliar.
2. Um Auxiliar pode ter zero, uma ou várias Rotinas.
3. Uma Rotina pode aparecer em mais de uma categoria — mas roda UMA VEZ.
   Categoria é etiqueta, não pasta.
4. Skill não tem dono nem agenda. É procedimento.
5. Artifact é sempre o resultado de alguém, nunca o próprio trabalho.
```

## A.3 Onde Briefing e Pesquisa passam a morar

**Briefing = Auxiliar de plataforma**, instalado por padrão em toda corretora.

Ele já tem tudo o que define um Auxiliar: agenda (`schedule_spec`), configuração
por empresa (`briefing_profiles` — que é literalmente o `tenant_auxiliaries.config`
que falta), execução durável (`work_runs`), e saída (`briefing_publications`).
**Falta apenas reconhecê-lo como Auxiliar em vez de item de menu.**

A tela continua existindo — **como a página daquele Auxiliar**, não como pilar.

**Pesquisa = Skill**, não página. Já existem **7 skills de pesquisa registradas e
ativas** e **zero pesquisas feitas**. A pesquisa nasce no chat; o resultado se
reencontra em Entregas.

**Monitor de pesquisa**, esse sim, é Auxiliar — é o Radar.

## A.4 O documento canônico

`docs/canon/ONTOLOGIA-DO-TRABALHO.md` — a definição, os corolários, os exemplos
de cada um, e **os erros já cometidos**, para que a LLM seguinte não os repita.

**Este documento é lido pelo bootstrap de sessão** (CLAUDE.md §2), junto com as
SPECs.

## A.5 Testes

`backend/tests/test_ontologia_e_unica.py`

| # | Prova |
|---|---|
| A1 | o documento canônico existe e tem as quatro definições |
| A2 | nenhuma Rotina existe sem Auxiliar dono |
| A3 | o termo "Auxiliar" não aparece na UI apontando para Rotina |
| A4 | Briefing está registrado como Auxiliar, não como rota de menu |
| A5 | as skills de pesquisa não têm Auxiliar próprio (são Skill) |

---

# BLOCO B — O menu, de sete pilares para cinco

## B.1 O menu hoje

```
AutoBrokers · Briefing · Pesquisas · Atendimentos · Auxiliares ·
Memórias · Personalização
```

Sete pilares. Dois deles são Auxiliares disfarçados.

## B.2 O menu depois

```
AutoBrokers      o chat
Atendimentos     as conversas com segurados
Auxiliares       TUDO que trabalha por você
Entregas         tudo que já foi feito, com link e histórico
Personalização   quem você é, seus dados, suas conexões
```

**Memórias** entra dentro de Personalização — é configuração de como o sistema
lembra de você, não um pilar.

## B.3 As rotas

| Rota hoje | Rota depois | O que acontece |
|---|---|---|
| `/dashboard/briefing` | `/dashboard/auxiliares/checklist-6h` | vira a página do Auxiliar |
| `/dashboard/pesquisas` | `/dashboard/entregas?tipo=pesquisa` | vira filtro em Entregas |
| `/dashboard/auxiliares` | `/dashboard/auxiliares` | **muda o conteúdo** (Bloco C) |
| `/dashboard/auxiliares/galeria` | — | absorvida pela página principal |
| `/dashboard/auxiliares/meus` | — | absorvida pela página principal |
| `/dashboard/auxiliares/rotinas` | — | vira aba dentro de cada Auxiliar |
| `/dashboard/auxiliares/execucoes` | `/dashboard/entregas` | unificada |
| `/dashboard/atividades` | `/dashboard/entregas` | unificada |
| `/dashboard/memorias` | `/dashboard/personalizacao/memorias` | |

**Toda rota antiga redireciona.** Ninguém encontra 404 — nem o corretor, nem um
link salvo, nem uma LLM lendo documentação velha.

## B.4 Testes

| # | Prova |
|---|---|
| B1 | o menu tem exatamente 5 pilares |
| B2 | nenhuma rota antiga devolve 404 — todas redirecionam |
| B3 | `/dashboard/auxiliares` não tem card intermediário |
| B4 | o princípio "o menu não cresce" está escrito e o teste conta os pilares |

---

# BLOCO C — A página de Auxiliares, e a página de cada um

## C.1 O que está errado hoje

```
clica em Auxiliares
   → vê 2 cards ("Rotinas prontas" e "Minhas rotinas")
      → clica num card
         → aí sim vê a galeria
```

**Três cliques para ver o que deveria estar na primeira tela.** E os auxiliares de
verdade não estão em nenhuma delas.

## C.2 A página principal

**Uma página só.** Referência de estrutura: a página de plugins do GPT Work e a de
conectores do Claude — **com a nossa identidade visual**.

```
┌────────────────────────────────────────────────────────────┐
│  Auxiliares                                                │
│  Trabalhadores que cuidam da sua corretora enquanto você    │
│  cuida do cliente.                                          │
│                                                             │
│  [ Todos ] [ Ligados ] [💰 Dinheiro que volta] [📈 Dinheiro │
│  novo] [🤝 Cliente blindado] [⚖️ Negociação] [🛡️ Proteção]  │
│  [⏱️ Tempo livre]                        [ 🔍 buscar     ]  │
│                                                             │
│  TRABALHANDO PARA VOCÊ                                      │
│  ┌──────────────┐ ┌──────────────┐                         │
│  │ Cobrança     │ │ Checklist    │                         │
│  │ Feita        │ │ das 6h       │                         │
│  │ ...headline  │ │ ...headline  │                         │
│  │ ● ligado     │ │ ● ligado     │                         │
│  └──────────────┘ └──────────────┘                         │
│                                                             │
│  DISPONÍVEIS                                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Caça-        │ │ Renovação    │ │ Organização  │        │
│  │ Comissão     │ │ Máxima       │ │ Completa     │        │
│  │ ...headline  │ │ ...headline  │ │ ...headline  │        │
│  │ EM BREVE     │ │ EM BREVE     │ │ EM BREVE     │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└────────────────────────────────────────────────────────────┘
```

**O card tem, e só:** nome · **uma headline que vende o ganho** · categoria ·
estado (ligado / disponível / em breve).

**A headline não descreve a função. Vende o resultado.**

```
✗ "Varre portais e envia boletos"
✓ "O boleto chega ao cliente antes de a apólice cancelar"

✗ "Analisa comissão por seguradora"
✓ "Descobre qual seguradora está pagando menos do que deveria"
```

## C.3 A página de cada Auxiliar

Hoje só existe um **modal de configuração** — sem nada que explique o que a coisa
faz ou por que vale a pena.

**A página passa a ter, nesta ordem:**

```
1. TÍTULO E HEADLINE
   a mesma copy do card, em tamanho grande

2. O QUE É
   um parágrafo, em português de corretor

3. O QUE ELE FAZ
   a lista de tarefas, com a frequência de cada uma

4. O QUE VOCÊ GANHA
   em número. Dinheiro, tempo ou risco evitado — com a conta.
   Se ainda não há número medido, diz o que será medido.

5. DE ONDE ELE TIRA A INFORMAÇÃO
   InfoCap · portal da seguradora · suas conversas · SUSEP
   (transparência: o corretor precisa saber o que o auxiliar acessa)

6. [ LIGAR ]  ou  [ CONFIGURAR ]  se já ligado

7. CONFIGURAÇÃO   (aparece depois de ligado)
   quando roda · para onde entrega · o que ignorar · limites

8. ROTINAS DESTE AUXILIAR   (aparece depois de ligado)
   cada uma com nome, horário, canal, e último resultado

9. HISTÓRICO
   as últimas execuções, com link para a entrega
```

**Decisão de UI:** página, não modal. Modal serve para uma decisão; isto é uma
leitura. **O modal permanece só para a edição rápida de uma rotina.**

## C.4 As seis categorias

Nomeadas pelo que o corretor **ganha**, não pelo que o sistema faz:

| Categoria | O que significa |
|---|---|
| 💰 **Dinheiro que volta** | o que é seu e está parado |
| 📈 **Dinheiro novo** | receita que existe e ninguém foi buscar |
| 🤝 **Cliente blindado** | a renovação antes de virar perda |
| ⚖️ **Negociação privilegiada** | o argumento que você não tem hoje |
| 🛡️ **Proteção da carteira** | o que não custa hoje e custa se acontecer |
| ⏱️ **Tempo livre** | a hora que volta pra você |

**Um Auxiliar pode ter mais de uma categoria.** Cobrança é *Tempo livre* e
*Dinheiro que volta* — e aparece nos dois filtros, sendo o mesmo Auxiliar.

## C.5 Testes

| # | Prova |
|---|---|
| C1 | a página principal mostra ativos e disponíveis sem clique intermediário |
| C2 | todo Auxiliar do catálogo aparece — nenhum invisível |
| C3 | todo card tem headline não vazia e diferente da descrição técnica |
| C4 | a página de cada um tem as nove seções |
| C5 | Auxiliar em "em breve" não tem botão de ligar ativo |
| C6 | filtro por categoria devolve o mesmo Auxiliar em duas categorias sem duplicar |

---

# BLOCO D — O catálogo

## D.1 A regra

```
TODOS visíveis. TODOS desligados. Nenhum roda sem o corretor mandar.
Os que não existem aparecem com etiqueta EM BREVE e a descrição já escrita.
```

**Por que os "em breve" entram agora:** para que você, eu e qualquer LLM futura
saibamos **onde cada coisa vai morar** antes de construí-la. Sem isso, o próximo
auxiliar nasce numa página nova — que é exatamente como chegamos aqui.

## D.2 O catálogo inicial

| Auxiliar | Categorias | Estado | O que faz |
|---|---|---|---|
| **Cobrança Feita** | ⏱️ 💰 | **existe** | acha inadimplente no portal, manda o boleto, e **responde se o cliente falar** |
| **Checklist das 6h** | todas | **existe como "Briefing"** | como está a corretora, o que aconteceu ontem, o que precisa de você hoje |
| **Primeira Mão** | ⚖️ | **existe como "Radar"** | mudança de regulação e de condição geral, antes de virar problema |
| **Caça-Comissão** | 💰 | EM BREVE | confere o extrato contra o esperado, apólice por apólice |
| **Contabilidade Pronta** | 💰 | EM BREVE | anexo do Simples, fator R, retenção — com o relatório pronto pro contador |
| **Clientes Perdidos** | 📈 | EM BREVE | quem foi cliente por anos e hoje não tem nada com você |
| **Venda Casada** | 📈 | EM BREVE | quem já é seu e só tem um produto |
| **Resgatar Cliente** | 📈 | EM BREVE | a cotação que esfriou e o ex-cliente na janela de revanche |
| **Renovação Máxima** | 🤝 | EM BREVE | o aumento que o cliente não vai aceitar, calculado antes de ele ver |
| **Sinistralidade Avançada** | ⚖️ | EM BREVE | qual seguradora vai apertar, e por que sua carteira vale mais |
| **Carteira Blindada** | 🛡️ | EM BREVE | uso não declarado, FIPE errado, apólice sem vistoria |
| **Organização Completa** | ⏱️ | EM BREVE | contato inválido, cadastro duplicado, apólice parada na entrega |
| **Digitação Zero** | ⏱️ | EM BREVE | lê o PDF da apólice e preenche o sistema |

**Cada "em breve" já nasce com:** nome, headline, categorias, o que faz, de onde
tira a informação, e **o que falta para existir**.

## D.3 O que morre

| Item | Por quê |
|---|---|
| `teste-runtime-smith-agent` | 0 execuções, archived |
| `teste-exclusivo-rafael` | 0 execuções, sem prompt |
| `teste-publicado-global` | 0 execuções, sem prompt |
| as 3 instalações correspondentes na Amandus | lixo de teste |
| rotina "Notícias Principais da Globo" | globo.com a cada 5 min, sem relação com seguros |

**O modelo de rotina "Notícias do setor" fica** — renomeado e recategorizado. É
legítimo, só nunca foi adotado.

## D.4 Testes

| # | Prova |
|---|---|
| D1 | todo Auxiliar do catálogo tem headline, categoria e origem de dados |
| D2 | nenhum Auxiliar nasce ligado |
| D3 | os itens de teste não existem mais em nenhuma tabela |
| D4 | Auxiliar "em breve" tem descrição completa — o teste procura campo vazio |

---

# BLOCO E — A entrega

## E.1 O defeito

`delivery_status = 'pending'` em **20 de 20** publicações de briefing. E
`backend/app/services/intelligence/delivery_policy.py:82` — a função que decide o
canal — **tem zero chamadores em produção.** É código morto testado.

`briefing_profiles.channels` existe, é escrito com `["dashboard"]`, e **nenhum
consumidor o lê**.

E o caminho antigo de WhatsApp foi **desligado de propósito**
(`legacy_adapter.py:34-37`, `INTELLIGENCE_CUTOVER` default ligado) **e o
substituto nunca foi construído.**

## E.2 Os canais

| Canal | Quando | O que leva |
|---|---|---|
| **Dashboard** | sempre | é o registro. Tudo aparece aqui. |
| **E-mail** | relatório, achado, artefato | o conteúdo completo |
| **WhatsApp** | achado urgente | **só a manchete de uma linha, com link** |
| **Push** | complemento | quando o navegador permitir |

**Regra:** o WhatsApp **nunca** leva o relatório inteiro. Leva a manchete e o
link. Isso é ao mesmo tempo melhor de ler e mais seguro contra bloqueio.

**E o e-mail nesta SPEC é o que já existe** (`email_service.py`, SendGrid, hoje
usado só para convite). O provedor definitivo é decisão da SPEC-069.

## E.3 A página Entregas

```
┌────────────────────────────────────────────────────────────┐
│  Entregas                                                   │
│  Tudo que foi feito por você.                               │
│                                                             │
│  [ Tudo ] [ Esta semana ] [ Por auxiliar ▾ ] [ Por tipo ▾ ] │
│                                                             │
│  hoje 06:02  ·  Checklist das 6h                            │
│  "3 coisas precisam de você hoje"           [ abrir ]       │
│                                                             │
│  ontem 09:14  ·  Cobrança Feita                             │
│  "4 boletos enviados, 1 sem WhatsApp válido" [ abrir ]      │
└────────────────────────────────────────────────────────────┘
```

**Unifica** `/dashboard/atividades`, `/dashboard/auxiliares/execucoes` e
`/dashboard/pesquisas`.

## E.4 A regra de dosagem

Herdada da SPEC-059 §15 e reforçada:

```
quiet hours ........ 20h às 08h, sem push
teto ............... 3 itens no diário, 5 a 7 no semanal
                     1 manchete por semana
crítico ............ fura o teto; nada mais fura
backlog ............ visível na página, NUNCA empurrado
```

**A lição que sustenta essa regra**, e vale escrever: todos os cards de meta do
InfoCap mostram *"0% ATINGIDA — MUITO ABAIXO DA META"* porque a meta nunca foi
cadastrada. **Um alerta que está sempre vermelho não é lido por ninguém.**

## E.5 Testes

| # | Prova |
|---|---|
| E1 | `delivery_policy.decidir()` é chamada em produção |
| E2 | `delivery_status` sai de `pending` quando a entrega acontece |
| E3 | falha de entrega registra o motivo — não fica em `pending` mudo |
| E4 | WhatsApp recebe manchete e link, nunca o relatório inteiro |
| E5 | teto diário respeitado; o excedente aparece no backlog |
| E6 | quiet hours respeitadas |
| E7 | Entregas mostra o que veio de todos os caminhos antigos |

---

# BLOCO F — Personalização por corretora

## F.1 O defeito

**Não existe jeito de configurar um Auxiliar depois de instalado.**

```
tenant_auxiliary_revisions ..... ZERO referências em código
                                 documentada em SPEC-058 §8.6, nunca criada
PATCH para tenant_auxiliaries.config .... NÃO EXISTE
```

As seis escritas em `tenant_auxiliaries` gravam `config` **no momento da
instalação e nunca mais**.

**E o lado da leitura está pronto e esperando:**
`backend/app/agents/auxiliary_context.py:169-178` prefere `tenant config.contract`
sobre `template default_config.contract` — **uma sobreposição por corretora que
nada no sistema consegue escrever.**

## F.2 A correção

**F.2.1 — A escrita existe.** Endpoint de configuração por corretora, com
histórico de revisão. Cada mudança grava quem mudou, quando e o quê.

**F.2.2 — Global e local nunca se misturam.**

```
o template GLOBAL é a origem
a config da CORRETORA é uma sobreposição
mudar o global NÃO apaga a sobreposição da corretora
mudar a corretora NUNCA toca no global
```

**Teste de isolamento com duas corretoras reais** (CLAUDE.md §7).

**F.2.3 — O auxiliar pergunta.**

> Corretor: *"não me manda mais o resumo de sábado"*
> Auxiliar: *"Combinado. **É sempre assim, ou só neste sábado?**"*
> Corretor: *"sempre"*
> Auxiliar: *"Ajustado. O resumo passa a vir só de segunda a sexta. Você pode
> mudar de novo quando quiser."*

**A pergunta é obrigatória.** Sem ela, o sistema não sabe se grava ou se obedece
uma vez.

**F.2.4 — E ele confirma o que gravou.** Sempre diz, em uma frase, o que mudou e
que vale só para ela.

## F.3 Testes

| # | Prova |
|---|---|
| F1 | a configuração pode ser escrita depois da instalação |
| F2 | mudar o global não apaga a sobreposição da corretora |
| F3 | mudar a corretora A não afeta a corretora B |
| F4 | o histórico de revisão registra quem, quando e o quê |
| F5 | ajuste sem a pergunta "é sempre assim?" não vira permanente |

---

# BLOCO G — A criação e a edição pelo chat

## G.1 O que existe

A ferramenta existe, está anexada ao grafo, **e por desenho nunca cria nada**:

`backend/app/agents/tools/factory_tool.py:88-89` e `:127-130` — todo retorno
termina instruindo o modelo a *"não instale, não crie rotina e não prometa que já
está funcionando."*

**E o funil está vazio:** `auxiliary_requests` = 0 e `capability_gaps` = 0 em 25
dias, com 502 work runs processados. **A ferramenta provavelmente nem está sendo
escolhida pelo modelo.**

## G.2 A correção

**G.2.1 — O chat passa a poder criar e editar.** Ligar, desligar, mudar horário,
mudar canal, ajustar o que entrega. Com aprovação para o que é irreversível.

**G.2.2 — Ele faz as perguntas certas.** Como no GPT Work: em vez de criar às
cegas, o chat pergunta o que falta.

> Corretor: *"quero um resumo diário das coisas importantes"*
>
> Chat: *"Posso montar. Antes preciso de três coisas:*
> *1. **Que assuntos** você quer priorizar? Minha sugestão: renovações da semana,*
> *cobranças em aberto, sinistros sem movimento.*
> *2. **Que horário?** Sugiro 6h, para você abrir antes do expediente.*
> *3. **Por onde** você quer receber — e-mail, WhatsApp ou só no painel?*
>
> *Você pode responder só: 'pode usar sua sugestão, 6h, e-mail'."*

**A regra:** o chat **sugere um padrão** e aceita "pode usar sua sugestão". Nunca
faz três perguntas abertas sem oferecer resposta.

**G.2.3 — O que ele cria é sempre visível.** Auxiliar ou Rotina criada pelo chat
aparece na página de Auxiliares imediatamente. **Nada nasce escondido.**

**G.2.4 — Global versus dela.** O chat **nunca** cria algo global. Tudo que nasce
pelo chat pertence àquela corretora. A promoção para global é decisão de admin.

## G.3 Testes

| # | Prova |
|---|---|
| G1 | o chat cria uma Rotina e ela aparece na página |
| G2 | o chat faz as perguntas antes de criar |
| G3 | "pode usar sua sugestão" é aceito e produz o resultado |
| G4 | nada criado pelo chat vira global |
| G5 | ação irreversível pede aprovação |

---

# BLOCO H — A limpeza

## H.1 O Portal Browser morre

**Provado:** todas as sessões com `real_action_allowed: false`, contas com
`credential_ref: null`, canários da Resulta **abortados** em 21/06.

**E existe ao lado do `portal_worker`, que funciona de verdade:** 18 varreduras
concluídas na Allianz, login real em `allianznet.com.br`, boleto de 116 KB
baixado, **API interna capturada.**

> **Duas coisas que fazem a mesma coisa — e a que aparenta ser mais sofisticada é
> a que nunca acessou nada.**

**Morre:** o código, as tabelas, as telas e a documentação. O `portal_worker` fica
e é o caminho único.

## H.2 O caminho de Auxiliar do Blueprint Center morre

`lib/admin/blueprint-studio-store.ts:173` → INSERT em `:230` gerou **exatamente
os 3 templates TESTE**. Nenhum Auxiliar de produção nasceu por ali.

**A parte de Agentes do Blueprint Center fica** — 2 releases publicadas, rollout
funcional. **Só a de Auxiliares morre.**

## H.3 As três tabelas fantasma

```
auxiliary_template_releases ..... 0 linhas, lido pelo código, nunca escrito
auxiliary_events ................ 0 linhas, `evento()` nunca chamado
tenant_auxiliary_revisions ...... 0 linhas, ZERO referências em código
```

**Decisão:** `tenant_auxiliary_revisions` **passa a ser usada** (Bloco F). As
outras duas: ou ganham escritor nesta SPEC, ou são apagadas junto com as colunas
de UI que dependem delas.

**Regra:** nenhuma tela pode mostrar coluna alimentada por tabela vazia. Hoje o
painel Factory mostra "Saúde", "Revisão" e "Último trabalho" — e as três estão
vazias no banco.

## H.4 Os campos que ninguém escreve

`tenant_auxiliaries.health`, `.last_run_at`, `.current_revision` — **nulos nas 5
linhas**, apesar de 4 execuções terem ocorrido. **Nenhuma linha de código os
escreve.** Ou passam a ser escritos, ou saem da tela.

## H.5 A ordem da limpeza

**Apagar é sempre o último passo.** Nunca antes de a estrutura nova existir e
passar nos testes.

## H.6 Testes

| # | Prova |
|---|---|
| H1 | nenhuma referência ao Portal Browser sobra em código, rota ou doc |
| H2 | os itens de teste não existem em nenhuma tabela |
| H3 | nenhuma tela mostra coluna de tabela vazia |
| H4 | `health`, `last_run_at` e `current_revision` são escritos, ou não aparecem |

---

# BLOCO I — O portal admin

## I.1 O P1 de segurança — não espera

`lib/admin/factory.ts:37` — `hasAdminCookie()` **apenas verifica a presença do
cookie `smith_admin_session`, sem validar assinatura nem expiração.**

E ele guarda: **criar template global** e **instalar em qualquer corretora**.

**Correção:** validar assinatura e expiração, como as rotas novas já fazem
(`requireMasterAdmin()` + `assertSameOrigin()`). **Este item sai na frente ou
junto com A–D. Não vai para o fim.**

## I.2 A desordem

O submenu "Inteligência" tem **9 itens** (`app/admin/layout.tsx:308-322`), dos
quais **4 respondem alguma variação de "o que o sistema pode fazer"**:
`capacidades`, `central-agentes`, `auxiliares`, `blueprint-center`.

E `/admin/routine-templates` tem **o mesmo rótulo** que uma página do corretor
("Rotinas prontas"), lendo outra tabela.

## I.3 A organização

```
Corretoras          empresas, conexões, memórias, identidade
Agentes             blueprint, releases, rollout — o que existe hoje e funciona
Auxiliares          catálogo global, publicação, instalação por corretora
Capacidades         Skills · Ferramentas · MCPs · Conectores
                    (quatro abas, um lugar só)
Operação            trabalhos, aprovações, filas, saúde
Inteligência        sinais, achados, briefings, demanda
```

**Regra:** cada conceito tem **um** lugar no admin. Se aparece em dois, um deles é
atalho declarado, nunca uma segunda fonte.

## I.4 O funil que nunca captou nada

`/admin/auxiliares/factory` é **somente leitura, sem um único botão**, e
`auxiliary_requests` = 0.

**Correção:** ou o funil ganha ação — transformar pedido em Auxiliar — ou a tela
sai. **Painel que só mostra zero é ruído.**

## I.5 Testes

| # | Prova |
|---|---|
| I1 | o cookie de admin é validado por assinatura e expiração |
| I2 | nenhum conceito tem duas telas-fonte no admin |
| I3 | nenhum rótulo do admin colide com um rótulo do dashboard |
| I4 | toda tela do admin mostra dado real ou não existe |

---

# BLOCO J — A documentação

## J.1 O problema

Toda LLM nova lê a documentação e se confunde — porque ela contradiz a si mesma.

**Exemplos medidos:**

```
EXECUTION-MASTER-PLAN.md marca SPEC-057 e 058 como "NÃO INICIADO"
   → o código existe, com 19 templates e tabelas no banco

app/dashboard/auxiliares/page.tsx:3-7 cita "SPEC-019 — Auxiliares = Rotinas"
   → esta SPEC revoga essa interpretação

graph.py:872 diz "RAG global OFF p/ attendance"
   → o código na linha 865 faz o contrário, e o código está certo

prompts.py:14 traz o cabeçalho "SPEC-013 P0"
   → CLAUDE.md §4 declara a SPEC-013 não-autoridade
```

## J.2 A correção

**J.2.1 — O glossário único.** `docs/canon/GLOSSARIO.md` — cada termo do produto,
com uma definição, um exemplo e onde ele mora no código. **Um termo, uma
definição.**

**J.2.2 — O painel volta a dizer a verdade.** `EXECUTION-MASTER-PLAN.md` é
reconciliado contra o que existe. Cada linha ganha a data da última verificação.

**J.2.3 — O legado é marcado, não apagado.** SPECs históricas ganham um cabeçalho
declarando o que nelas ainda vale e o que foi superado — e por qual SPEC.
**Apagar perde a razão de ser das decisões; deixar sem marca confunde.**

**J.2.4 — Os comentários mentirosos morrem.** Comentário que contradiz o código
ao lado é pior que comentário nenhum. Varredura dirigida nos arquivos que a
auditoria apontou.

**J.2.5 — O README.** Reescrito para responder, em uma página: o que é o produto,
quais são as peças, onde cada uma mora, e o que ler antes de mexer.

## J.3 Testes

| # | Prova |
|---|---|
| J1 | o glossário existe e cobre os termos da ontologia |
| J2 | nenhuma SPEC canônica contradiz outra sobre os quatro termos |
| J3 | o painel de execução bate com o que existe no código |
| J4 | os comentários apontados pela auditoria foram corrigidos |

---

# 3. Migrations

| Migration | O que faz |
|---|---|
| `..._064_01_auxiliary_catalog.sql` | catálogo com categorias, headline, estado, origem de dados |
| `..._064_02_tenant_config_write.sql` | `tenant_auxiliary_revisions` passa a existir de fato |
| `..._064_03_delivery_channels.sql` | canais e estado de entrega por publicação |
| `..._064_04_limpeza.sql` | remove itens de teste — **por último** |

Todas idempotentes, expand-first, com APPLY/VERIFY/ROLLBACK escritos antes.
**Ler `MIGRATIONS-AUTHORITY.md` antes de qualquer SQL.**

---

# 4. Gate final

```
[ ] os 5 testes do Bloco A          [ ] os 5 testes do Bloco F
[ ] os 4 testes do Bloco B          [ ] os 5 testes do Bloco G
[ ] os 6 testes do Bloco C          [ ] os 4 testes do Bloco H
[ ] os 4 testes do Bloco D          [ ] os 4 testes do Bloco I
[ ] os 7 testes do Bloco E          [ ] os 4 testes do Bloco J
[ ] a suíte inteira verde
[ ] nenhuma rota antiga devolve 404
```

## 4.1 A prova viva

```
1. abrir Auxiliares          → todos aparecem, em uma tela, com headline
2. abrir um "em breve"       → explica o que fará e não deixa ligar
3. ligar a Cobrança          → aparece em "trabalhando para você"
4. pedir ajuste pelo chat    → ele pergunta "é sempre assim?"
5. conferir a outra corretora → não mudou nada
6. abrir Entregas            → tudo que foi feito, com link
7. procurar Portal Browser   → não existe mais em lugar nenhum
```

---

# 5. Riscos

| Risco | Mitigação |
|---|---|
| mudar rota quebra link salvo | toda rota antiga redireciona; teste conta 404 |
| apagar antes de a nova estrutura existir | apagar é sempre o último passo |
| headline virar marketing vazio | toda headline tem de citar um ganho concreto; o teste procura verbo de resultado |
| catálogo com "em breve" demais frustrar | máximo de 10 "em breve" visíveis; o resto fica no admin |
| corretora perder configuração na migração | backfill copia o que existe antes de qualquer mudança |

---

# 6. O que NÃO pode acontecer

```
✗ segunda tabela de Auxiliar ao lado de tenant_auxiliaries
✗ segunda página de catálogo
✗ Rotina existindo sem Auxiliar dono
✗ Auxiliar novo nascendo fora do catálogo
✗ conceito com duas definições em dois documentos
✗ apagar SPEC histórica sem marcar o que foi superado
```
