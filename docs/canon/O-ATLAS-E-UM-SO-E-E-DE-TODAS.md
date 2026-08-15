---
> **Status:** canônico · **Criado em:** 15/08/2026
> **Autoridade:** decisão do Founder, 15/08/2026, registrada em `FOUNDER-DECISIONS.md`
> **Função:** impedir que qualquer executor — humano ou LLM — trate o Atlas como
> propriedade de uma corretora. Ele nunca foi.
---

# O Atlas é UM SÓ, e é de todas

> **Leia isto antes de tocar em `ura_maps`, no Tecelão, no Cartógrafo, nos
> playbooks, nos corredores ou em qualquer prompt de atendimento.**

---

## 1. A frase que resolve a confusão

```text
Não existe "o mapa da Resulta" nem "o mapa da AutoFleet".
Existe O MAPA — da AutoBrokers — que TODAS as corretoras preenchem juntas.
```

A Resulta e a AutoFleet são apenas **as duas primeiras** a contribuir. As
próximas corretoras que parearem o celular vão preencher rotas que hoje estão
vazias, e **todas** passam a usar o que qualquer uma descobriu.

---

## 2. Por que ele existe — e é a única coisa que importa

Um agente de atendimento não pode travar no meio de um acionamento com um
segurado esperando.

Se o mapa já tem a rota, o agente **sabe de antemão**:

```text
quais perguntas a URA vai fazer, e em que ordem
qual tecla corresponde a qual serviço
o que precisa ser clicado, e o que vem depois
```

Sabendo a pergunta antes de ela chegar, ele já tem a resposta pronta. **Ele não
erra porque não está adivinhando.** É por isso que **quanto mais rotas, melhor** —
e por isso que juntar o que todas as corretoras percorreram é o desenho, não um
efeito colateral.

Uma pessoa pede um eletricista na Allianz Residencial: a rota está no mapa, o
passo a passo está no playbook, o canal está no corredor. Os três existem para a
mesma coisa — o atendimento sair certo na primeira vez.

---

## 3. Como o mapa cresce

```text
rota que o mapa JÁ TEM         → descartada, não precisa
rota NOVA, que ninguém viu     → entra no mapa
```

Simples assim, e cumulativo. Com o tempo o mapa fica preenchido. Rotas raras
levam mais tempo a aparecer — e tudo bem. **As rotas comuns são as que os agentes
não podem errar**, e são as que se completam primeiro, porque são as mais
percorridas.

⚠️ **Corolário para quem for medir cobertura:** uma rota `gap` não é defeito do
mapa. É rota que ninguém pisou ainda. Dizer "o mapa está incompleto" sem separar
*"nunca foi percorrida"* de *"foi percorrida e não gravamos"* é medir a coisa
errada.

---

## 4. 🔴 O que NUNCA pode entrar no mapa

**Identidade de corretora ou de atendente.** Nem nome, nem razão social, nem
apelido.

| ❌ errado no mapa | ✅ certo no mapa |
|---|---|
| `"*Saionara - Resulta*, vou te transferir…"` | `"{NOME} - {CORRETORA}, vou te transferir…"` |
| `"Olá RESULTA CORRETORA DE SEGUROS LTDA"` | `"Olá {CORRETORA}"` |
| `"Maria Regina - Autofleet Seguros"` | `"{NOME} - {CORRETORA}"` |

**E o motivo não é privacidade — é que o agente é global.**

```text
A estrutura de atendimento é GLOBAL.
O DASHBOARD é que a transforma em atendimento personalizado da corretora.
```

O nome da corretora e o da atendente vêm da **configuração**, em tempo de
execução. Um mapa que já traz "Resulta" escrito dentro está **errado por ser
específico onde tinha de ser neutro** — e vai fazer o agente da corretora seguinte
se apresentar com o nome de outra empresa.

O mesmo vale para **playbooks, corredores e prompts**. Nenhum deles carrega nome
de corretora.

⚠️ Dado pessoal de segurado — CPF, CNPJ, placa, telefone, endereço — também não
entra, e isso é regra separada (CLAUDE.md §7). Vale para os **nós e para as
arestas**: 📊 em 15/08/2026 os nós estavam mascarados e as arestas não, com 141
CPF gravados como rótulo de aresta. Ver `PENDENCIAS.md#P-162`.

---

## 5. O erro de leitura que este documento existe para matar

> 📊 Em 15/08/2026 eu abri a pendência **P-165** classificando a agregação entre
> corretoras como **"P1 cross-tenant"** — um vazamento a corrigir, e propus ao
> Founder decidir entre "mapa global" e "mapa por corretora".
>
> **A pergunta estava errada.** A agregação é o produto. O que estava errado eram
> os NOMES dentro dela.
>
> Eu cheguei nisso por um caminho que parece rigor e não é: apliquei a regra de
> isolamento entre corretoras (CLAUDE.md §7) a um artefato que **não é dado de
> corretora** — é conhecimento sobre a URA de uma seguradora, que é a mesma para
> todo mundo. A regra é certa; o objeto era outro.

**O teste que separa os dois casos, e que vale para qualquer artefato novo:**

```text
Este dado descreve a SEGURADORA?  → é do Atlas, é global, agregue.
Este dado descreve a CORRETORA
ou a pessoa que atende?           → NÃO entra. Vem da configuração.
```

O menu da Porto é o mesmo para a Resulta, para a AutoFleet e para a corretora que
entrar em dezembro. O nome de quem apertou o botão não é.

---

## 6. Onde isto está escrito, para não se perder de novo

| lugar | o que diz |
|---|---|
| este arquivo | a doutrina inteira |
| [`CLAUDE.md`](../../CLAUDE.md) §2 | ponteiro no bootstrap de sessão |
| [`PENDENCIAS.md`](PENDENCIAS.md) P-162 · P-164 · P-165 | os defeitos abertos que decorrem daqui |
| `backend/app/services/atlas/weaver.py` | cabeçalho do construtor do mapa |
| `backend/app/services/ura_map_service.py` | cabeçalho de quem lê o mapa |

Os dois cabeçalhos de código existem porque quem vai errar isto de novo é quem
abre o arquivo, não quem abre a documentação.
