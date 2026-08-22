# RASCUNHO — as SPECs que ainda vão ser escritas

> ⚠️ **Isto é anotação, não SPEC.** Existe para que nada do que o Founder pediu se perca
> entre uma sessão e outra. Cada item vira SPEC detalhada no momento certo, com juiz
> crítico em laço até liberar — o processo que levou a SPEC-084 de 54 a 98.
>
> Criado em 22/08/2026, ao fechar a SPEC-084.

---

## A FILA

| # | nome | depende de | estado |
|---|---|---|---|
| **085** | O destravamento não trava em silêncio | SPEC-084 ✅ | rascunhada abaixo |
| **086** | O Suporte Humano só é chamado quando alguém espera | — | rascunhada abaixo |
| **087** | A rota se atualiza quando a URA muda | SPEC-084 ✅ | rascunhada abaixo |
| **088** | A Central de Agentes em grupos | — | rascunhada abaixo |
| **089** | 🔴 **O ENSAIO — levar as rotas ao nível da máquina de lavar** | SPEC-084 ✅ | **a mais urgente** |
| **090** | 🔴 **A FÁBRICA DE INTELIGÊNCIA — o que fazer quando uma corretora nova pareia** | — | ideia do Founder, 22/08 |
| **091** | 🔴 **O MAPA DOS PROCESSOS — todo processo do sistema documentado para LLM** | 090 | ideia do Founder, 22/08 |

---

# 089 · O ENSAIO

**O problema, em uma frase:** a SPEC-084 fez o corredor **falar com a URA** em 41 rotas.
Ela não fez a atendente **conduzir o cliente**, e não fez ninguém **provar ponta a ponta**.

📊 Medido em 22/08/2026:

```
o corredor fala com a URA .............. 41 de 73    média 47,8/96
a atendente sabe conduzir .............. 2 de 73     regras_para_o_cliente
o cliente recebe protocolo+dia+período . 0 de 73     client_summary
alguém provou ponta a ponta ............ 1 de 73     a máquina de lavar
apelidos: chaveiro / bateria / pneu .... 0           a máquina de lavar tem 11
```

**As quatro entregas, na ordem em que pagam:**

1. **Apelidos, do acervo.** As palavras que os clientes já usaram para pedir cada serviço.
   🔴 Sem isso o acionamento morre antes de começar.
2. **`regras_para_o_cliente` e `expectativa_do_desfecho`** em toda rota que pontua.
   Lidos das telas da URA, não escritos de cabeça.
3. **`client_summary`** — protocolo + dia + período chegam ao segurado. Hoje: zero rotas.
4. **O ensaio por rota**, o mesmo que a máquina de lavar teve antes da Clarissa:
   transcrição turno a turno, âncoras conferidas contra o corpus, teste que chama o motor,
   simulação do "oi" ao protocolo. **Os três juízes em cada uma.**

**Prioridade:** as 31 rotas de `allianz` (auto e residencial), `hdi`, `yelum` e `porto` auto.
📊 Hoje 4 delas chegam a 60 e nenhuma passou pelo ensaio.

---

# 090 · A FÁBRICA DE INTELIGÊNCIA

> *"A corretora ABC contrata o AutoBrokers e vai parear o celular. As conversas vão para o
> nosso banco. A partir daí precisam virar inteligência."* — o Founder, 22/08

**O que a SPEC tem de responder, passo a passo, para qualquer LLM executar sozinha:**

### As sete transformações

```
CONVERSAS BRUTAS no banco
   │
   ├─ 1. TRIAGEM       o que é conversa com SEGURADORA · com CLIENTE · interna
   │                   🔴 e o que é ATENDENTE HUMANO falando (a lição da 084: 29% do acervo)
   │
   ├─ 2. ATLAS         as telas de URA viram mapa observado (o Tecelão já faz)
   │
   ├─ 3. ROTAS         seguradora × ramo × serviço que ainda não temos
   │                   → corredor novo · subserviço novo · apelidos novos
   │
   ├─ 4. PLAYBOOK      as telas viram passos, com âncora e tecla
   │                   🔴 medidos contra o corpus, nunca escritos de cabeça
   │
   ├─ 5. CARTAS        conversa com cliente vira conhecimento para o RAG
   │                   🔴 SÓ o que é INÉDITO — ver "o problema do excesso"
   │
   ├─ 6. INSTRUÇÃO     o que a atendente aprende a perguntar e avisar
   │
   └─ 7. RELATÓRIO     o que deu certo, o que ficou torto, o que ajustar
                       🔴 é o insumo da automação futura
```

### 🔴 Os três venenos que a SPEC tem de matar

**1 · Contaminação.** *"Às vezes uma atendente humana respondeu algo errado e isso corre o
risco de virar informação verdadeira."*

- toda carta carrega **a fonte e a data**
- resposta de humano é **candidata**, não verdade — precisa de confirmação (a seguradora
  repetiu? aconteceu de novo? existe documento?)
- 💭 possível: nível de confiança por carta, e o RAG pesa por confiança

**2 · Excesso.** *"Terão 1000 cartas sendo destiladas da mesma coisa."*

- antes de destilar, **perguntar ao RAG se já sabemos** — só o inédito entra
- 💭 dedup semântica com teto por tema, e o teto **cai** conforme o acervo cresce
- 🔴 a métrica não é quantas cartas produziu — é **quantas perguntas o RAG passou a
  responder que antes não respondia**

**3 · Regressão.** *"Não regredir jamais, mas aproveitar tudo que aumente a qualidade."*

- toda mudança de corredor passa pelo comparador da SPEC-084
- 🔴 e ele agora sabe distinguir **casar a tela** de **responder certo** (CLAUDE.md §9.5)
- carta nova nunca apaga carta antiga sem prova de que a antiga estava errada

### O que o Founder faz, e o que a máquina faz

A SPEC diz, em cada passo, se é 🤖 automático ou 🧑 do Founder — e quando for do Founder,
**quanto tempo custa e o que exatamente ele olha**. O plano Max entra na destilação em
volume; a SPEC tem de dizer **como disparar isso** e **o que conferir depois**.

---

# 091 · O MAPA DOS PROCESSOS

> *"Processos detalhados de todas as áreas. Para qualquer LLM entender como tudo funciona,
> com clareza, sem erros, com regras, com tarefas."* — o Founder, 22/08

**A ideia dele, e ela é boa.** O que a torna melhor:

### 🔴 Um processo documentado que ninguém executa apodrece

A diferença entre documentação e processo vivo é **o gate**. Cada processo mapeado ganha:

```
· o passo a passo, em linguagem de execução (não de descrição)
· 🔴 o CONTROLE: como saber que o passo funcionou — e como ele pode FALHAR
· o relatório de saída, num formato fixo, no lugar fixo
· e a métrica de quantas vezes rodou e quantas deu certo
```

**Sem o controle, é manual. Com o controle, é processo.** Foi essa diferença que fez a
SPEC-083 e a 084 valerem: cada regra veio com a query que a produziu.

### Os processos a mapear (lista inicial — a SPEC amplia)

```
onboarding de corretora nova     · pareamento de WhatsApp
destilação de conversa em carta  · criação de corredor novo
criação de auxiliar              · criação de Skill
publicação de Artifact           · execução de SPEC (o que fizemos aqui)
resposta a incidente             · rotação de credencial
```

### 🔴 A sugestão que faz a ideia dele dar um salto

**O relatório de cada execução vira o insumo do próximo.** Não é arquivo morto: é
**a base de evidência da automação futura**.

```
processo roda  →  relatório com o que deu certo e o que doeu
               →  N relatórios do mesmo processo
               →  o padrão do que sempre dá errado fica VISÍVEL
               →  só então automatiza — e automatiza o que já se sabe que funciona
```

> **Automatizar antes de medir é automatizar o erro.**

### O que pesquisar antes de escrever

- como as empresas grandes documentam procedimento para LLM (Anthropic Skills, OpenAI
  function/tool specs, "agent SOPs")
- se existe ferramenta open-source de **runbook executável** que se possa acoplar
- 🔴 e o que já existe DENTRO do AutoBrokers — a SPEC-056 (Skills) e a SPEC-058
  (Auxiliares/Rotinas) já definem peças disso. **Consolidar antes de criar.**

---

# 085 · O DESTRAVAMENTO NÃO TRAVA EM SILÊNCIO

A cadeia Vigia → Sentinela → Cérebro → suporte humano. O defeito de origem:
`missing_slots → needs_human → estado terminal → ninguém tenta de novo`.
Já há conserto parcial (o `fallback_adaptive`), mas nunca foi medido em produção.

🔴 **Espera a 084 fechar** — os 8 passos que respondiam errado e o `subservice_supported`
mudaram o terreno desta SPEC.

# 086 · O SUPORTE HUMANO SÓ É CHAMADO QUANDO ALGUÉM ESPERA

O grupo recebia alerta de conversa que ninguém esperava. Conserto aplicado (marcador
compartilhado no Redis, teto de lembretes, "só avisa quem espera") — falta medir se
funcionou e fechar as bordas.

# 087 · A ROTA SE ATUALIZA QUANDO A URA MUDA

Detectar → propor → juiz → aprovar. 📊 A azul migrou a URA em 07/04/2026 e duas teclas
morreram — ninguém percebeu até a SPEC-084. **Depende do Atlas e do corpus**, ambos
prontos agora.

# 088 · A CENTRAL DE AGENTES EM GRUPOS

*"Está muito confuso para mim."* Agrupar por propósito, cada grupo com sua página, fluxo
e explicação. Independente de tudo o resto.
