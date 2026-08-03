# Corredores que dá para criar — e o que falta em cada um

> **03/08/2026** · SPEC-063 Bloco F · 📊 tudo medido no banco de produção
> `dcajcvlzcjbmyapmklil`. Pedido do Founder: *"me traga uma lista dos corredores
> que vc recomenda que devemos fazer, que as atendentes têm capacidade de
> executar, mas ainda não criamos o corredor"*.

---

## O que existe hoje

📊 **11 corredores** em `corridor_playbooks.py` — 1 residencial (Allianz) e 10
de auto (allianz, porto, hdi, yelum, tokio, alfa, azul, bradesco, mapfre,
zurich).

📊 Os 10 de auto cobrem **quatro subserviços**:

```
guincho · bateria · pneu · chaveiro
```

## O critério que usei

Um corredor só pode ser criado se houver **evidência para escrevê-lo**. Três
fontes, e a mais importante é a primeira:

```
mapa de URA VIVO      o roteiro observado do menu de WhatsApp da seguradora
                      sem ele, o corredor seria adivinhação
cartas publicadas     o que o agente sabe dizer sobre aquela seguradora/ramo
playbook de conduta   como se conduz aquele tipo de atendimento
```

**Sem mapa de URA vivo, não recomendo criar** — seria escrever um roteiro para
uma conversa que ninguém observou. É exatamente como nasceram os 50
`corridor_runs` abandonados que hoje estão no cemitério.

---

## 🟢 RECOMENDO CRIAR — a evidência está pronta

### 1 · Vidros de auto, nas 10 seguradoras que já têm corredor

**É a maior lacuna, e a mais barata.** 📊 O que já existe:

```
playbook de conduta  auto/vidros ....... ATIVO, destilado de 16 atendimentos
telefone dedicado .... todas as 22 seguradoras têm campo `vidros` no seed
portal do prestador .. `glass_service_portal_url` — e há DOIS portais de vidro
                       no catálogo (o mesmo prestador serve várias seguradoras)
cartas ............... allianz 439 · yelum 276 · tokio 251 · hdi 184 · porto 165
```

E 📊 **`_AUTO_SUBSERVICES` tem `guincho, bateria, pneu, chaveiro` — vidros não
está lá.** O produto sabe conversar sobre vidro, tem o telefone, tem o portal do
prestador, e **não tem o corredor**.

> Vidro é o serviço de auto mais frequente depois de guincho, e é o que menos
> exige do segurado: CPF, data e relato. É o candidato número um.

**O que falta:** os `ura_steps` do fluxo de vidros em cada seguradora. O Atlas
já tem o mapa vivo das 10 — é leitura, não campo novo.

### 2 · Pane seca / combustível — auto

📊 O classificador do Atlas já reconhece (`pane seca`, `combustivel`), e o
`_AUTO_SLOTS_COMMON` já cobre os dados necessários (é o mesmo do guincho, sem
destino). **Falta só declarar o subserviço.** É o corredor mais barato da lista.

### 3 · Residencial nas 4 seguradoras que já têm mapa

Hoje só a **Allianz** tem corredor residencial. 📊 Com mapa de URA vivo e cartas
suficientes:

| Seguradora | cartas residencial | mapa URA | sessões observadas |
|---|---:|:---:|---:|
| **Bradesco** | 46 | ✅ | 15 |
| **Porto** | 27 | ✅ | 139 |
| **Tokio** | 20 | ✅ | 36 |
| **Yelum** | 19 | ✅ | 86 |

**Porto primeiro** — é a seguradora com mais sessões observadas de todas (139),
mesmo tendo menos cartas residenciais.

### 4 · Os subserviços residenciais que faltam na própria Allianz

📊 A família Allianz Residencial planejava **5 subcorredores** e tem **1**:

```
electrician ........... ✅ existe, com 8 slots e 10 golden tests
plumber (encanador) ... ❌  — e há playbook de conduta ATIVO, 22 atendimentos
residential_locksmith . ❌  — playbook em DRAFT, só 3 atendimentos
unclogging ............ ❌  — sem playbook
home_appliances ....... ❌  — sem playbook, mas o guardrail do eletricista
                             JÁ manda rotear para cá
```

**Encanador é o próximo.** É o único com conduta ativa e base real (22
atendimentos), e o eletricista já existe como molde a copiar.

---

## 🟡 DÁ PARA CRIAR, MAS COM RESSALVA

### 5 · Auto nas 2 seguradoras de cauda com mapa

📊 `azul` (16 cartas de auto) e `alfa` (18 em "outro"). Têm mapa de URA vivo e
já têm corredor de auto registrado — o que falta é **exercitá-los**, não
criá-los. Recomendo provar os 10 existentes em modo teste antes de somar novos.

---

## 🔴 NÃO RECOMENDO CRIAR AGORA

### Youse — e o motivo é do produto, não da falta de dado

📊 **177 cartas de auto** — seria a 5ª maior. Mas:

```
mapa de URA vivo .......... 0
sessões observadas ........ 0
```

E o próprio código explica, em `insurer_registry.py`: *"SEM WhatsApp de
assistência — acionamento por app/telefone (3003 5770 / 0800 730 9901). **Nunca
tentar WhatsApp**."*

> **Corredor neste produto é conversa por WhatsApp.** A Youse não tem esse
> canal. Criar um corredor para ela exigiria telefonia — que 📊 **não existe em
> nenhuma linha do repositório** (zero `twilio`, `asterisk`, `dtmf`), embora
> haja credenciais Twilio no ambiente, sem consumidor.
>
> **Para a Youse, o caminho certo é handoff humano** — e é o que o sistema deve
> fazer, dizendo o motivo.

### Sura · MetLife · AXA · Sompo · Suhai

📊 Entre 19 e 55 cartas, e **zero mapa de URA, zero sessão observada**. Há
conhecimento para o agente *falar* sobre elas, e nenhuma observação para
*acionar* com elas. Escrever corredor aqui seria adivinhar.

**O que destrava:** religar o Observador e deixar o Atlas ver alguns
atendimentos reais dessas seguradoras. É trabalho do tempo, não de código.

---

## Ordem que eu executaria

```
1  vidros de auto           10 seguradoras · maior volume, menor esforço
2  pane seca                declarar subserviço · o mais barato de todos
3  encanador (Allianz)      conduta ativa, 22 atendimentos, molde pronto
4  residencial Porto        139 sessões observadas — a mais vista de todas
5  residencial Bradesco/Tokio/Yelum
6  provar os 10 de auto     em modo teste, antes de somar mais
```

## O que NUNCA deve virar corredor

**Sinistro.** Em nenhuma seguradora, em nenhum ramo. 📊 O playbook já trata
`sinistro` como gatilho de handoff (`handoff_triggers`), e a SPEC-063 F.2.5
mantém isso. Sinistro envolve perícia, documento e decisão de cobertura — é
conversa de gente.

E **onde não há corredor, o caminho é handoff** — com o motivo dito ao cliente,
nunca silêncio nem improviso.
