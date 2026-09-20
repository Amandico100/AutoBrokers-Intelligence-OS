# EXTRA-001.5 · O canário, passo a passo — o que o Founder faz para provar que funciona

> **Para quem:** o Founder, sozinho, no navegador e no WhatsApp. Nada aqui exige terminal.
> **Escrito em:** 18/09/2026 · **Vale para:** o código empurrado na `main` pela SPEC-EXTRA-001.5.
> 🔴 **A ordem importa.** O passo 2 é o que faz a base responder; sem ele, tudo responde
> *"ainda não sabemos"* — que é honesto, e é exatamente o que a SPEC promete quando não há linha publicada.

---

## Passo 0 · Implantar (5 min)

No EasyPanel, clique **Implantar** em **dois** serviços, nesta ordem:

```
1. smith-api     (o backend, a Skill e a base de planos)
2. smith-web     (a tela de Conhecimento mudou)
```

⚠️ **Estar na `main` não é estar no ar.** Enquanto não clicar, o produto continua com o código de ontem.

**Confira a variável, no `smith-api` → Environment:**

```
POLICY_INTELLIGENCE_V2 = true      <- se estiver ausente ou false, A SKILL NÃO RODA
```

📊 Medido em 18/09: a variável não existe no `.env` de desenvolvimento, e o código a trata como **desligada** quando
ausente (`backend/app/core/feature_flags.py`). Se ela estiver desligada em produção, todo o canário abaixo vai medir
o comportamento **antigo** e concluir errado. Confira antes de qualquer pergunta.

No `smith-web`, confirme que existem `NEXT_PUBLIC_API_URL` e `BACKEND_INTERNAL_API_KEY` (sem eles a tela abre, mas
os blocos vêm vazios).

---

## Passo 1 · Abrir a tela nova (2 min)

```
Painel → Personalização → Conhecimento
```

Você vai ver **dois blocos novos**:

| bloco | o que mostra | o que esperar hoje |
|---|---|---|
| **Cobertura dos planos** | seguradora × ramo, com quantos planos e serviços e de que documento vieram | ~~8 seguradoras, 17 combinações, todas ainda **não publicadas**~~ → **desde 20/09: 8 seguradoras, 20 combinações, 108 planos e 492 serviços PUBLICADOS** |
| **Fila de curadoria** | cada linha proposta, com o trecho da página ao lado | ~~📊 **73 serviços** e **33 planos** esperando revisão~~ → **desde 20/09: 8 linhas** (táxi da Azul) |

🔴 **O que a tela NÃO pode mostrar:** nome de tabela, nome de coluna, SQL ou `insurer_key`. Se aparecer, é defeito —
me avise.

🔴 **Troque de corretora (Resulta ↔ AutoFleet) e volte.** Os números têm de ser **os mesmos**, e a tela diz por quê
numa linha: a base de planos é global, é a mesma para todas as corretoras. Isso é de propósito (D-PILOTO-01): o que a
HDI cobre no plano Essencial não muda conforme a corretora.

---

## Passo 2 · ✅ **FEITO — não precisa mais fazer** (mantido como história)

> Em 19/09 você publicou as primeiras 23 linhas. Em **20/09** a base inteira foi destilada e publicada
> (📊 492 serviços, 108 planos, 8 seguradoras) — veja a seção **TESTE DA EXTRA-001.5.2** no fim deste
> documento. **Não há mais fila para curar**, salvo 8 linhas de táxi da Azul que estão retidas de propósito.

### ~~Publicar as primeiras linhas (15 min) — é o passo que destrava tudo~~

Na **Fila de curadoria**, filtre por uma seguradora e um ramo onde você conheça o produto.
💭 Sugestão: **HDI · residencial** (📊 2 planos e as linhas de serviço correspondentes).

Para cada linha:

```
1. leia o TRECHO DA PÁGINA que aparece ao lado (os termos do serviço vêm grifados)
2. a linha diz o que a página diz?   SIM -> Publicar     NÃO -> Rejeitar (escreva o motivo)
```

**O que acontece quando você publica a primeira linha:** o **plano** daquela linha também passa a valer. A tela
avisa isso antes (*"ao aprovar, o plano X (nível N, p. M) também passa a valer"*). É assim porque a resposta ao
segurado precisa do plano **e** da linha — publicar só a linha deixaria o produto mudo.

⚠️ **Publique só o que você leu.** O banco recusa publicar sem revisor, e o seu usuário fica gravado na linha. Isso
é proposital: uma extração feita por modelo **propõe**; quem publica é gente.

💭 **Dez linhas bastam** para os testes abaixo. Não precisa curar a fila inteira hoje.

---

## Passo 3 · Os 8 casos — o que perguntar, e o que provam

**Onde:** casos 1 a 5 e 7 no **chat `core`** do painel da Resulta (a sua conta). Caso 6 no **WhatsApp**, do aparelho
de teste. Caso 8 é comigo.

🔴 **Os casos 5, 7 e 8 são os que dão direito à conclusão.** Sem eles, "funcionou" pode ser um `return` fixo no topo
da função. Não os pule.

| # | o que perguntar | o que tem de acontecer | o que prova |
|---|---|---|---|
| **1** | *"o segurado <nome> tem carro reserva?"* — use um cliente **da seguradora e ramo que você publicou** | responde **sim ou não**, diz o **nome do plano** e termina com a fonte: *"(Condições gerais da HDI, p. 24.)"* | o caminho inteiro: apólice → plano → linha → fonte |
| **2** | a mesma pergunta, num cliente de uma seguradora **que você não publicou** | *"Ainda não tenho as condições da <seguradora> para esse produto na base."* — 🔴 **nunca** "não cobre" | não saber ≠ não cobrir. É a distinção que a SPEC existe para garantir |
| **3** | *"qual o limite do guincho dele?"* | um número **com unidade** (km, dias, acionamentos) e a página | limite sem unidade é proibido pelo banco |
| **4** | a mesma pergunta num cliente de **plano mais baixo**, quando existe um plano acima publicado | além da resposta, aparece o gancho: *"o plano acima teria… — a <atendente> pode avaliar na renovação"*, **sem preço** | o gancho comercial existe e não promete o que não pode |
| **5** | a mesma pergunta num cliente do **plano mais alto** | **nenhum** gancho aparece | 🔴 controle do caso 4: prova que o gancho não é um texto fixo |
| **6** | no **WhatsApp do aparelho de teste**, mande: *"cobre granizo?"* | mesma verdade do painel, em linguagem de conversa, com a origem em português | o atendente do WhatsApp usa o mesmo cérebro do chat — o que você pediu |
| **7** | no chat `core`: *"quantas parcelas faltam para o segurado <nome>?"* | responde sobre parcelas e **não** consulta a base de planos | 🔴 controle: a base só entra em pergunta de cobertura |
| **8** | (comigo) derrubar a busca de propósito | *"Não consegui abrir a apólice dele agora"* — texto **diferente** do caso 2 | falha de sistema ≠ lacuna de conhecimento |

**Anote, para cada caso:** ✅ passou · ⚠️ passou mas o texto ficou estranho · ❌ falhou (cole a resposta).

---

## Passo 4 · A validação com a Saionara e a Regina (20 min)

Mostre a elas os casos 1, 2 e 4 e pergunte, com estas palavras:

```
· dá para conferir de onde veio a resposta? você abriria o documento na página que ele citou?
· quando ele diz "ainda não sabemos", isso soa honesto ou soa que o sistema falhou?
· o gancho do plano superior soa útil, ou soa empurrão de venda?
· a fila de curadoria dá para revisar sem abrir o PDF? o trecho na tela basta?
```

📊 A Saionara é a dona do caso de referência (a apólice da HDI cujo cadastro escondia R$ 125,94, 41 % do prêmio).
**Peça a ela as perguntas que ela faria, não os dados dos clientes.**

Registre cada resposta como: **não testado** × **canário técnico** × **validado pela atendente**. São três coisas
diferentes, e só a terceira conta como pronto.

---

## O que NÃO é defeito (para não me chamar à toa)

```
· "ainda não sabemos" numa seguradora que você não publicou ....... é o comportamento certo
· a fila mostrar 73 linhas esperando .............................. é o trabalho de curadoria, não um erro
· a tela não mudar ao trocar de corretora ......................... a base é global, de propósito
· o gancho dizer "nossa equipe" em vez do nome da atendente ....... pendência P-E0015-05, já registrada
· seguradora da carteira sem nenhuma linha ........................ falta a condição geral no acervo (fila da onda 3)
```

---

## Depois: as seguradoras que faltam

A base responde pelo que está no **acervo de condições gerais** (📊 hoje: 8 seguradoras, 194 documentos). As que
faltam estão listadas, **na ordem do prêmio da carteira**, em:

```
docs/canon/providers/susep/fila-onda-3.json      19 seguradoras
```

Quando a condição geral de uma delas entrar no acervo, o extrator roda sobre ela e as linhas aparecem na fila —
**sem código novo**. É por isso que destilar mais seguradoras não era pré-requisito desta SPEC.

---

# TESTE DA EXTRA-001.5.2 — a base de planos responde

> **Escrito em 20/09/2026.** É este o teste que vale hoje. Os passos 1 a 4 acima continuam válidos como
> descrição das telas; o **Passo 2 (publicar) está feito** — 📊 a base saiu de 23 para **492 serviços
> publicados, em 108 planos e 8 seguradoras**, destilados dos documentos por leitores e conferidos linha
> a linha contra a página.

## A · Implantar primeiro (5 min)

No EasyPanel, clique **Implantar** em **smith-api**, **smith-worker** e **smith-web**. Isso sobe o vocabulário
novo (a palavra *"vidraceiro"*), a tela da fila com o parecer e o extrator v2.

⚠️ **A base já está no banco** — ela não depende do Implantar. O que depende é o vocabulário e as telas.
`POLICY_INTELLIGENCE_V2` já está **true** no ambiente.

## B · As perguntas, uma por seguradora (10 min)

No chat `core` do painel e no WhatsApp do aparelho de teste, com **uma apólice real de cada seguradora**:

```
· "meu seguro cobre guincho? até quantos km?"
· "tenho carro reserva?"
· "cobre chaveiro?"
· "cobre vidraceiro?"        (numa apólice RESIDENCIAL)
```

**O que esperar** — a resposta diz sim ou não, **com o limite** (km, diárias, R$ por evento). No chat do
corretor vem também o **documento e a página**. No WhatsApp, a mesma verdade, sem citação.

📊 O que a base responde hoje, para você comparar (medido contra a base real, passando o nome exato do plano):

| seguradora · plano | pergunta | resposta esperada |
|---|---|---|
| Tokio auto · VIP | cobre chaveiro? | coberto, até R$ 200,00 por evento |
| Yelum auto · Superior | tenho carro reserva? | coberto, 10 diárias |
| Yelum auto · Essencial | tenho carro reserva? | **não** coberto — "Não se aplica para este Plano" |
| Yelum auto · Básico | guincho até quantos km? | coberto, com as **duas** hipóteses (sinistro 300 km; pane, menor) |
| HDI auto · VIP | cobre guincho? | coberto, sem limite de km em sinistro |
| Bradesco auto · nº 43 | cobre guincho? | coberto, até 200 km |
| Porto residencial · Conforto | cobre encanador? | coberto, R$ 150,00 por serviço |
| Porto residencial · Veraneio Conforto | cobre vidraceiro? | **não** coberto |
| Allianz residencial · Essencial | tem hospedagem? | **não** coberto |
| Azul auto · cláusula 37N | cobre guincho? | coberto, 500 km, **reembolso com teto** |
| Mapfre auto | cobre guincho? | **"ainda não sei"** — e está **certo**: o documento no acervo não descreve a assistência |

## C · 🔴 O que anotar se vier "ainda não sei"

Esta é a parte mais importante do teste. A base guarda o nome do plano **como o documento escreve**
(ex.: `CLÁUSULA 37N – LIVRE ESCOLHA 500 KM`); a apólice do segurado pode escrever só `37N`. Quando os dois
não casam, a resposta vira *"ainda não sei"* — honesta, **nunca errada**, mas inútil.

```
Se a apólice TEM plano e a resposta foi "ainda não sei":
anote EXATAMENTE como o nome do plano aparece na apólice (copie e cole) + a seguradora.
```

Isso é a pendência **P-E00152-07**, e só apólice real mede. Mapfre auto é a exceção conhecida: ali o
"ainda não sei" é a resposta correta, não um defeito.

## D · A Fila de Curadoria (2 min)

```
Painel → Personalização → Conhecimento → Fila de curadoria
```

**Devem aparecer 8 linhas, e só elas:** táxi da Azul, retidas porque o limite fora do município está
incompleto. Se aparecer **mais** que isso, me avise.

## E · O que NÃO é defeito, na versão de 20/09

```
· Mapfre auto dizer "ainda não sei" ................... falta o manual da assistência no acervo
· Allianz não responder por MOTO, CAMINHÃO ou FROTA ... só o AUTOMÓVEL foi destilado
· Bradesco condomínio quase vazio ..................... os documentos de condomínio não têm assistência 24h
· Zurich, Alfa e as outras sem nenhuma linha .......... não há documento no acervo
· as 8 linhas de táxi da Azul na fila ................. retidas de propósito (P-E00152-08)
```
