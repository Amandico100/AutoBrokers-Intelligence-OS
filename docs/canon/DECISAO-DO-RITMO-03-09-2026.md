# A DECISÃO DO RITMO — como executar mais SPECs por janela de 5h sem perder o que o protocolo entrega

> Escrito pelo orquestrador em 03/09/2026, ao fechar a SPEC-094, a pedido do Founder: **três sugestões com nota, comparadas
> ao protocolo v11.2 em qualidade e tempo, e uma recomendação.** Enquanto o Founder decide, o protocolo fica **pausado** —
> nenhuma SPEC nova começa. Números 📊 vêm dos relatórios em `reports/` e do `subagent_tokens` que o harness devolve; 💭 é estimativa.

---

## 1. O que foi medido — sem enfeite

```
                         088 (PADRÃO, v11)    093-B (CRÍTICO, v11)    094 (CRÍTICO, v11.1→v11.2)
relógio de trabalho       3h35                 7h15                    ≈ 9h em 3 janelas
tokens de subagentes      💭 ≈1,5 M            📊 ≈3,0 M               📊 ≈2,8 M (+0,4 M das pesquisas da 094.1)
janelas que acabaram      0                    1                       2
nota                      90                   88                      {NOTA_094}
blockers que só o painel
ou a auditoria viram      5                    7 + 1 + 2               12 (2 lentes + red team)
```

📊 **Três janelas de 5h morreram em 24 horas** (06:30, 10:40, ~17:00), cada uma custando ~3h parado e agentes mortos no meio de
edição. **E o custo que ninguém mediu até agora é o do orquestrador:** esta sessão é UM chat contínuo desde 02/09 22:40. Cada
turno meu reenvia o contexto inteiro (💭 centenas de milhares de tokens), dezenas de vezes por janela. O `CLAUDE.md` §9 já dizia
*"recomendada uma sessão nova por SPEC"* — e eu não segui, por conveniência de contexto. **INFERÊNCIA: o contexto do
orquestrador é o maior consumidor da janela, maior que qualquer subagente, e é o mais fácil de cortar sem perder qualidade.**

**O que o painel achou de fato, por frente, nas três SPECs** (quem paga o próprio custo):

| frente | 088 | 093-B | 094 | custo típico |
|---|---|---|---|---|
| red team | — | 5 quebras (detector, nota, truncado…) | 7 quebras (janelas, NaN, injeção, fail-open…) | 📊 200–225k |
| lente do DADO / auditoria | — | 2 blockers que ninguém viu | 2 blockers (cobertura no Artifact; fixture cega) | 📊 195–245k |
| verdade/ELO/regressão | 1+3 blockers (3 lentes) | 3 blockers | 2 blockers de GUARDA (produto ok) | 📊 127k |
| juiz de confirmação | — | 1 defeito criado pelo conserto | (juiz fresco) | 📊 ~200k |
| aquecimento | rebaixou o nível certo | 3 emendas | **15 emendas + um 📊 meu refutado** | 📊 153k |

**Conclusão honesta:** o **red team** e a **lente do dado** são as duas frentes que colocam defeito de produto na mesa; a lente de
"verdade/regressão" acha defeitos de guarda; o aquecimento é o melhor custo-benefício de todos. Mutação por cópia e gate zero
pegaram regressão real três vezes — não saem em nenhuma opção.

---

## 2. As três sugestões

### A · "Sessão nova por SPEC, protocolo intacto" — nota **78**
O que muda: **um chat por SPEC**, aberto com um HANDOFF de uma página (estado, branch, decisões abertas, URL do dossiê) em vez do
histórico inteiro. Nada muda no v11.2. O orquestrador continua Fable.
- **Qualidade:** igual (0 de perda).
- **Tempo por SPEC:** igual (CRÍTICO 6–8h de trabalho; PADRÃO 3–4h).
- **Tokens:** 💭 −60 a −70% do orquestrador; subagentes iguais (≈2,5 M por CRÍTICO). Resultado: 💭 **1 CRÍTICO inteira por janela, sem
  morrer no meio** — hoje não fecha uma.
- Por que não é a recomendação: não chega perto de "duas por janela".

### B · "Três marchas + sessão nova por SPEC" — nota **88** ← **recomendação**
É a ideia do Founder ("dar peso às SPECs") tornada mecânica. O nível já existe no protocolo (§3); o que muda é **quanto custa cada
nível** e **quem decide** (a conta do card, sem pedir permissão):

```
LEVE      RISCO ≤ 3, SUPERFÍCIE 1, nada envia, nada cross-tenant, sem migration
          o orquestrador EXECUTA (builder = Fable) · Sonnet reroda guardas e mutações · SEM painel · aquecimento de 6 perguntas
          💭 0,3–0,5 M tokens · 1–2h                                                       ex.: 094.1 BLOCO C (listar_entregas), P-094-PRODUCAO-500
PADRÃO    RISCO 4–5 ou SUPERFÍCIE 2
          1 builder Opus · desenhista SÓ se houver guarda novo · painel = RED TEAM apenas · confirmação MECÂNICA (Sonnet reroda
          guardas + mutações do conserto) · sem juiz fresco
          💭 1,0–1,3 M · 3–4h                                                              ex.: 095, 097
CRÍTICO   RISCO 6+, SUPERFÍCIE 3, ou o piso da §3.2 (envia, cross-tenant, migration de dado, credencial)
          = v11.2 como está: desenhista · 2 lentes (verdade+regressão · DADO) + red team · juiz fresco (confirma + audita)
          💭 2,3–2,6 M · 6–8h                                                              ex.: 094.1, 096, 098
```
Mais duas regras que valem para as três marchas: **sessão nova por SPEC** (o corte de A) e **o card da SPEC diz o nível e o orçamento
antes de começar; se o orçamento da janela não cabe a SPEC inteira, ela não começa — começa a próxima LEVE/PADRÃO da fila.**
- **Qualidade:** CRÍTICO igual. PADRÃO: 💭 perde ~1 blocker por SPEC (os que a lente do dado/verdade pegariam; o red team fica). LEVE:
  depende do orquestrador não se enganar — por isso a definição é estreita e a mutação é obrigatória.
- **Tempo:** 💭 **2 SPECs por janela quando uma delas é LEVE ou PADRÃO** (ex.: 095 PADRÃO 3–4h + 094.1 BLOCO C LEVE 1h + começo da
  próxima). Duas CRÍTICO na mesma janela continua utopia (6–8h cada) — o que se ganha é não morrer no meio.
- **Tokens:** 💭 −40 a −55% no total da leva, porque metade da fila não é CRÍTICO. As propostas 097/098 têm cara de PADRÃO/CRÍTICO;
  o Founder decide o nível quando discordar do card.

### C · "Opus 5 orquestra, Fable converte e revisa" — nota **72**
O que muda: cada SPEC roda num chat novo com **Opus 5** como orquestrador; Fable entra só na conversão (a SPEC definitiva + aquecimento)
e numa revisão final do relatório.
- **Qualidade:** 💭 perda pequena-a-média. Nesta leva o orquestrador foi quem pegou o que os subagentes não pegaram: o diagnóstico
  dos 99 vermelhos (o builder atribuiu ao "ambiente"), a fusão pelo teste do produto, o P1 da conta compartilhada virando gate.
  Opus 5 faz isso, mas o histórico mostra que o "erro de julgamento silencioso" custa mais que tokens.
- **Tempo:** igual por SPEC.
- **Tokens:** cai o preço por token; mas a barra "Fable" e a barra "todos os modelos" são separadas no plano — trocar o maestro
  alivia uma e carrega a outra. Ganho real: 💭 −20 a −30%.
- Quando faz sentido: se, com B, as janelas ainda morrerem. Aí C soma a B (B+C), não substitui.

### Continuar como está — nota **45**
A qualidade é a maior da história do projeto (88–90, defeitos reais pegos antes do piloto), **mas uma SPEC CRÍTICO por duas janelas,
três interrupções por dia e um chat de 24 horas não é ritmo — é sobrevivência.** A entrega vale; o jeito de chegar nela, não.

---

## 3. A recomendação, em uma linha
**B, agora: três marchas com orçamento no card, sessão nova por SPEC, mutação e aquecimento em todas as marchas.** Se em duas
janelas ainda morrer uma no meio, somar C. Nunca cortar mutação, gate zero ou aquecimento — é onde o dinheiro do protocolo está.

## 4. Os próximos passos, na ordem (depois da decisão)
```
1  094.1 · A fábrica de relatórios   CRÍTICO (fonte externa + Approval) — mas o BLOCO C (listar_entregas) sai antes como LEVE
2  095   · Artifact & Delivery Hub   PADRÃO provável (tela, sem envio) — converter medindo
3  096   · Chat runtime / shell      CRÍTICO (toca o chat inteiro)
4  097   · A operação tem uma casa   PADRÃO/CRÍTICO — converter medindo (proposta + research pack já na pasta)
5  098   · Cada coisa sabe de quem é CRÍTICO (identidade/escopo cross-tenant — piso da §3.2)
6+ 099 → 114 conforme o MASTERPLAN da pasta, 2 a 4 convertidas por vez, avaliação de bloco em bloco como agora
```
