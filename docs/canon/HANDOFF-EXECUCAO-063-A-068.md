# Entrada para quem vai executar as SPECs 063 a 068

> **Escrito em 01/08/2026**, no fim da sessão que produziu as sete SPECs.
> **Este é o primeiro documento a ler.** Ele diz o que ler depois, em que ordem,
> e o que NÃO fazer.

---

## 1. Onde o projeto está, em cinco linhas

```
o conhecimento está pronto ......... 8.916 cartas de 8.800 atendimentos reais
o atendimento NÃO pode ser ligado .. há um P0 (ver §3)
a InfoCap está fora do ar .......... HTTP 500, e é bug deles
nada está pareado .................. por decisão do Founder
sete SPECs escritas ................ 46 blocos, 229 testes, nenhuma executada
```

---

## 2. A ordem de leitura

**Não pule, e não leia fora de ordem.**

```
1. CLAUDE.md                              as regras invioláveis
2. docs/canon/pesquisa/00-LEIA-PRIMEIRO.md
                                          o que descobrimos e por que importa,
                                          em português de negócio
3. docs/canon/pesquisa/03-PLANO-DE-EXECUCAO.md
                                          o plano completo, com as decisões
                                          de arquitetura já tomadas
4. a SPEC da vez                          063 primeiro
5. docs/canon/MIGRATIONS-AUTHORITY.md     ANTES de qualquer SQL
```

**Só depois disso, o código.**

### 2.1 Os documentos de apoio, e quando cada um serve

| Documento | Quando ler |
|---|---|
| `pesquisa/01-ACHADOS-COMPLETOS.md` | quando precisar do detalhe técnico: URLs, números, armadilhas verificadas |
| `ESTADO-DA-CAMPANHA.md` | para entender a destilação de conhecimento e as 23 pendências registradas |
| `INFOCAP-CORPAPI-MAPA.md` | antes de qualquer coisa que toque InfoCap |
| `AUDIOS-RESGATE.md` | quando o WhatsApp for reconectado |
| `FOUNDER-DECISIONS.md` | antes de decidir arquitetura |
| `CHANGE-ADDENDA.md` | o histórico de mudanças além do texto das SPECs |
| `POLITICA-SEGURANCA-CONHECIMENTO-GLOBAL.md` | antes de qualquer coisa que cruze dado entre corretoras |

---

## 3. O P0 que você precisa saber antes de tudo

**Se o agente de atendimento for ligado hoje, quem responde o segurado é o
copiloto interno do corretor** — cujo prompt manda entregar CPF sem mascarar.

```
Resulta · AutoBrokers (core) ....... criado 21/06 00:36 · ATIVO
Resulta · Saionara (atendimento) ... criado 21/06 04:45 · desligado
```

A integração grava `agent_id = NULL` por um ternário que devolve a mesma coisa
nos dois ramos. Sem `agent_id`, o sistema escolhe **o agente ativo mais antigo**.

**É o Bloco A da SPEC-063.** Está resolvido no papel e não no código.

---

## 4. As sete SPECs, e a ordem

```
063 · Atendimento e Canais Confiáveis .....  8 blocos · 41 testes · EXECUTÁVEL
064 · A Ontologia e a Casa Limpa .......... 10 blocos · 48 testes · EXECUTÁVEL
065 · A Carteira e o Dinheiro Visível .....  7 blocos · 35 testes · BLOQUEADA*
066 · O Acervo: SUSEP e o RAG .............  7 blocos · 31 testes · EXECUTÁVEL
067 · O Descobridor .......................  8 blocos · 46 testes · depende de 64-66
068 · Prontidão e Go-Live .................  6 blocos · 28 testes · o portão
069 · Canais Definitivos ..................  ⏸️ CONGELADA — futura
```

**\* A 065 está bloqueada pela API da InfoCap (HTTP 500).** Está escrita inteira
de propósito: **quando a API voltar, é executar, não replanejar.** E os Blocos D
(portal) e F (o harness que calcula) **não dependem dela** — podem ser feitos
enquanto isso.

### 4.1 O que 063 e 064 têm de especial

**Podem ser discutidas em paralelo — não se tocam.** E são as duas que mais mudam
o que o Founder consegue ver e mostrar.

---

## 5. A regra que atravessa todas: o Bloco 0

**Toda SPEC começa com uma auditoria obrigatória.** Nenhuma linha de código antes
dela.

```
1. cada afirmação da SPEC ainda é verdade hoje?
2. o que mudou desde que ela foi escrita?
3. o que ela não previu?
4. o que pode ser melhor do que está escrito?
5. o que vai quebrar?
```

**O relatório vai ao Founder antes da execução:**

```
✅ CONFIRMADO · ⚠️ CORRIGIDO · ➕ ACRESCENTADO · ❓ EM ABERTO · 🚫 RETIRADO
```

**Sem esse relatório aprovado, a execução não começa.**

**Por que isso é regra:** na sessão que escreveu estas SPECs, seis auditorias
mudaram o plano seis vezes, e três acharam defeitos que teriam ido para produção.
**A auditoria não atrasa a execução — evita a reexecução.**

---

## 6. As decisões de arquitetura já tomadas

**Não reabra sem motivo novo. Estão fundamentadas no plano.**

| Decisão | O que ficou |
|---|---|
| **Auxiliar é nomeado pelo que o corretor GANHA** | não por setor, não por função técnica |
| **Auxiliar TEM Rotina. Auxiliar NÃO É Rotina** | hoje o produto inverteu isso |
| **Corredores: mantemos** | não competem com o RAG — o RAG fala com o segurado, o corredor com a URA da seguradora |
| **Portal Browser morre** | 100% simulação, ao lado do portal worker que funciona |
| **Meta oficial fica para depois do piloto** | decisão do Founder; a SPEC-069 está congelada |
| **Proxy: não** | nenhuma evidência de que reduz bloqueio; há evidência contra |
| **Número vai para tabela, cláusula vai para RAG** | embutir R$ 37 bilhões em texto convida o modelo a errar aritmética |
| **Ingestão de condições gerais é universal e sob demanda** | gatilho: alguma corretora tem apólice viva desse produto |
| **"Garimpo" continua sendo a voz do corretor** | o achador de dinheiro chama-se **Descobridor** |

---

## 7. O que NÃO fazer

```
✗ ligar o agente de atendimento antes da SPEC-063
✗ parear qualquer WhatsApp sem o Founder mandar
✗ executar a 065 antes de a API da InfoCap voltar
✗ executar a 069 — está congelada
✗ apagar qualquer coisa antes de a estrutura nova existir e passar nos testes
✗ criar motor paralelo a qualquer um listado no CLAUDE.md §5
✗ aplicar SQL sem ler MIGRATIONS-AUTHORITY.md
✗ inventar preço, plano ou cobrança (CLAUDE.md §13.6)
```

---

## 8. O que está pendente do lado do Founder

**Nenhuma bloqueia o começo. Duas ficam caras se decididas tarde.**

```
1. o telefonema à InfoCap ....... a API responde 500, e é bug deles.
                                  No mesmo telefonema: pedir a liberação das
                                  permissões (comissão, sinistro, endosso).
                                  É a única coisa com fila de terceiro.

2. a lista de corredores ........ todas as seguradoras que Resulta e AutoFleet
                                  atendem, por ramo. Sai de perguntar às
                                  atendentes, não de código.

3. FIPE ......................... a API interna funciona; eles declaram
                                  publicamente que não oferecem API.
                                  ⚠️ sem ela não existe a análise de taxa
                                  efetiva de renovação — a de maior valor.

4. benchmark entre corretoras ... a política de 14/07 diz que o global nunca é
                                  acessível por corretora. Agregado derivado
                                  não está claramente permitido nem proibido.

5. aviso visível da Evolution ... cláusula de licença, para produto white-label

6. Google Business Profile ...... destrava a família de marketing

7. conselho tributário .......... até onde vamos: disclaimer, revisão por
                                  contador, ou parceria formal
```

---

## 9. O estado técnico, medido

**Tudo verificado entre 30/07 e 01/08/2026.**

```
BANCO
  cartas publicadas no RAG ........... 8.916
  conversas encerradas ............... 8.872
  memórias da corretora .............. 0        ← SPEC-067 Bloco H
  briefings publicados ............... 20, todos em `pending`
  auxiliares que rodaram .............. 4, todos manuais, há 52 dias
  pesquisas feitas ................... 0, com 7 skills ativas
  detectores de negócio .............. 0 de 12

CÓDIGO
  o chat principal executa código? ... NÃO      ← SPEC-065 Bloco F
  consulta dados? .................... NÃO
  calcula? ........................... NÃO
  limitação de taxa no envio? ........ NÃO      ← SPEC-063 Bloco C
  handoff notifica alguém? ........... NÃO      ← SPEC-063 Bloco B

EXTERNO
  API da InfoCap ..................... HTTP 500 nas duas contas
  portal da Allianz .................. FUNCIONA — 18 varreduras, boleto real
  repositório SUSEP .................. FUNCIONA — verificado à mão, 72 versões
  suíte de testes .................... 102 arquivos, todos verdes
```

---

## 10. O achado que dá o tom do produto

Extraído do portal da Allianz em 15/07/2026, dado real da Resulta:

```
ramo                          apólices    prêmio        comissão
─────────────────────────────────────────────────────────────────
2013 · Residência Digital         3       R$   593,83   R$ 17,76   → 2,99%
2024 · Empresa PME                1       R$ 1.297,56   R$  0,00   → ZERO
```

**Idêntico em 11/07 e em 15/07. Congelado assim há semanas.**

Ou a comissão é zero de verdade — e a corretora vende um produto que não paga
nada, sem saber. Ou é erro de cadastro — e há comissão a cobrar.

> **Nos dois casos o corretor precisa saber. E hoje ninguém olha.**
>
> **É isso que o produto faz. Todo o resto é infraestrutura para isso acontecer.**
