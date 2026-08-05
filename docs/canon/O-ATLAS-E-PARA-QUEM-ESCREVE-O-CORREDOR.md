# O Atlas é para quem escreve o corredor — não para o agente ler na hora

> **Decisão do Founder, 05/08/2026.** Este documento existe para que a próxima
> sessão não reabra a discussão sem os números que a fecharam.
>
> **Quem chegar aqui perguntando "por que não ligamos o Alfaiate / a promoção de
> mapa / a atualização automática de rota" — a resposta está na §5, e ela tem
> prazo, não é definitiva.**

---

## 1. O que o Atlas é, em uma frase

O **mapa das telas** do WhatsApp de cada seguradora: que menu aparece, que
opções ele oferece, e para onde cada opção leva.

Ele foi criado para uma coisa só: **saber a rota de cada clique**, para que o
acionamento de assistência não seja às cegas.

## 2. Para quem ele NÃO é

**Não vai para o prompt do agente de atendimento.** Foi medido, e o resultado é
o contrário do esperado.

📊 Para um acionamento de **guincho na Allianz**, o bloco do mapa entregaria:

```
tamanho ..................... 5.220 caracteres
o prompt tem hoje ........... 5.098    → DOBRARIA

o menu de serviço AUTO ...... posição 31   ← o corte é de 30. FICA DE FORA.
telas de guincho ............ posições 56, 61 e 64
telas de pneu ............... posição 161

das 30 telas que ENTRARIAM:
  19  não têm opção nenhuma (avisos, perguntas abertas)
   6  são conversa de gente ("Ok", "Um momento", "Com quem falo?")
   2  são de OUTRO RAMO (Dedetização, Substituição de Telhas)
   1  é útil para um guincho
a "tela inicial" anunciada .. "Termo de Privacidade" — sem opções
```

**Num caso de guincho, com o carro parado na estrada, o prompt ofereceria
dedetização e troca de telhas como opções válidas.**

### As três causas, e nenhuma é "o mapa está mal feito"

1. **O mapa é `ramo='todos'`.** Uma seguradora tem UM WhatsApp e UMA URA; a
   árvore mistura auto, residencial, condomínio e empresarial. E o renderizador
   não recebe o caso — não sabe que é auto, não sabe que é guincho.
2. **O renderizador não imprime `leads_to`.** Ele lista tela e opções, sem
   ligação entre telas. Ou seja: **ele não diz o que vem depois** — que era
   exatamente o propósito. 📊 E só 38% das opções da Allianz e 19% das da Porto
   têm destino gravado.
3. **Ordenar por "tela mais vista" promove o boilerplate.** O que mais se repete
   numa URA não é a decisão — é o termo de privacidade, o "Ok", o "aguarde".

## 3. Para quem ele É

> **O Atlas é a lista de trabalho de quem escreve o corredor.**

📊 Cruzando as 38 âncoras do corredor `allianz-auto` com o mapa: das **231 telas
de menu**, 90 já têm resposta escrita e **141 ficam órfãs**.

Essa lista de 141 é a próxima tarefa, escrita sozinha. E os **6 menus órfãos
mais frequentes valem 48% de todas as aparições órfãs** — seis telas, uma tarde
de trabalho, resolvido para sempre.

Ler o mapa uma vez e transformar em âncora é **permanente, determinístico e
custa zero em tempo de atendimento**. É o oposto de injetar cinco mil caracteres
e torcer.

**Quem lê o mapa:** o Founder, um chat como este, e as telas de admin. Nunca o
agente em tempo de atendimento.

## 4. O percentual de cobertura — o que ele mede de verdade

📊 A "cobertura de 37%" **não** significa *"mapeamos 37% da URA"*. `compute_coverage`
casa **opção oferecida** com **aresta percorrida**. Ela responde:

> *Dos botões que apareceram nos menus, em quantos vimos alguém clicar?*

Os outros 63% são botões que existem e a corretora **nunca escolheu** — seguro
viagem, segunda via, consulta de sinistro. Coisas que ela não pede.

**Nunca chegaremos a 100%, e não deveríamos querer.** Chegar exigiria a corretora
apertar todos os botões de todas as URAs, inclusive os que não usa.

⚠️ **Pendente:** o Founder pediu um percentual que reflita a realidade do
atendimento — contando como *mapeado* tudo aquilo de que se sabe o que vem
depois, inclusive resposta em texto livre e inclusive os botões que ninguém vai
apertar. Isso ainda não foi implementado. Ver `PENDENCIAS.md`.

## 5. O que fica DESLIGADO, e por quanto tempo

📊 **Nunca aconteceu um acionamento.** `work_runs` com `workflow_key ilike
'%acionamento%'` = **0 linhas**. O sistema nunca acionou uma seguradora.

Automatizar o conserto de uma rota antes do primeiro acionamento existir é
resolver um problema que ainda não temos — e cada peça ligada é uma peça que
pode piorar o que ainda nem começou.

| Peça | Estado | Por quê |
|---|---|---|
| promover mapa para `active` | 🔴 **não fazer** | liga a Sentinela, que liga o Alfaiate, que escreve overlay em playbook sozinho |
| Alfaiate (`playbook_tailor`) | 🔴 **não ligar** | 📊 não é uma IA — é uma expressão regular de 26 caracteres, e nunca rodou uma vez |
| Sentinela de Rotas | 🟡 roda e é inerte | 📊 `route_drift` = 0 linhas desde sempre, porque não há mapa `active` para comparar |
| atualização automática de rota | 🔴 **não fazer** | 📊 89% das conversas da Allianz terminam com um humano da seguradora; mapear rota resolve a minoria do caminho lá |
| Tecelão (redesenha o mapa) | 🟢 **manter ligado** | é o que produz a lista de trabalho da §3 |
| Observador | 🟢 **manter ligado** | é a matéria-prima de tudo |

> **Quando revisar:** depois que os agentes de atendimento estiverem ligados e
> acionamentos reais tiverem rodado. Aí saberemos onde eles travam de verdade —
> e será esse o problema a automatizar, não o que imaginamos hoje.

## 6. O alerta do Atlas é interno. Ponto.

📊 `route_sentinel._canal_de_plataforma` varre `companies` e usa o **primeiro
canal elegível** — ou seja, o aviso de que a Porto mudou um botão sairia pelo
WhatsApp de uma corretora qualquer.

**Está errado, e o Founder foi direto:**

> *"O Atlas é para inteligência interna do nosso sistema de atendimento. Não tem
> nada a ver com as corretoras pareadas. Elas não precisam saber de merda
> nenhuma — só querem que o agente atenda bem."*

O aviso mora no **Portal Admin**, e em lugar nenhum mais. Nunca no canal de um
tenant.

---

## 7. O que o agente de atendimento usa, então

| Peça | O que dá |
|---|---|
| **Corredor** (`corridor_playbooks`) | âncora → resposta, sem LLM. Slots obrigatórios, captura de protocolo, freio de teste, política de tela desconhecida |
| **Orientação escrita** (`human_phase_guidance`) | a regra que ninguém deduz. 📊 668 caracteres — a melhor razão valor/caractere do prompt |
| **Ficha** (`attendance_ficha`) | "JÁ CONFIRMADO / AINDA FALTA para poder acionar", a cada turno |
| **Guarda determinístico** (`guard_human_phase_reply`) | recusa resposta vazia, texto longo demais, e **qualquer sequência de 5+ dígitos que não esteja nos dados do caso** |

**O que falta no corredor não é mapa. É âncora** — e o mapa é justamente quem
diz quais faltam.

---

## 8. Uma decisão relacionada, do mesmo dia

O prompt do acionamento **se contradizia** sobre a única decisão irreversível
que existe:

```
regra 3 do sistema ....... "CONFIRME com a opção afirmativa"
a orientação do corredor . "NAO confirme: exige aprovação da corretora"
                            ↑ e o prompt apresenta este bloco como
                              "vale mais que a sua intuição"
```

A frase de não-confirmar nasceu quando `DISPATCH_FINALIZE_MODE` era `test` e o
Founder testava no próprio celular. O modo virou `live` e o texto ficou.

**Decisão do Founder:** o agente **confirma sozinho**. Ele é o responsável pelo
atendimento e não pede aprovação de ninguém.

E a proteção deixou de ser *"não confirme"* — que só adiava o trabalho para um
humano — e passou a ser **conferir antes**: placa, serviço, origem e destino
contra os dados do caso. Se os quatro conferem, confirma. Se algum diverge,
corrige ou responde `NAO_SEI`.

> Uma checagem explícita e verificável vale mais que uma proibição, porque a
> proibição só garante que nada acontece.
