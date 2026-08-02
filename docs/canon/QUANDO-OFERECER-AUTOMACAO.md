# Quando o chat oferece automatizar — e quando fica quieto

> **Documento canônico.** Lido no bootstrap, junto com a
> [`ONTOLOGIA-DO-TRABALHO.md`](ONTOLOGIA-DO-TRABALHO.md).
> **v1.0 · 02/08/2026 · SPEC-064 Bloco F/G**, a partir de correção do Founder.

---

## O problema que este documento resolve

A SPEC-064 F.2.3 escreveu esta cena:

> Corretor: *"não me manda mais o resumo de sábado"*
> Auxiliar: *"Combinado. **É sempre assim, ou só neste sábado?**"*

**O Founder apontou duas coisas erradas, e as duas procedem.**

**1. A pergunta não comunica nada.** *"É sempre assim?"* pede uma confirmação
sem dizer o que está em jogo. O corretor responde "sim" sem saber que acabou de
criar uma automação — ou responde "sim" achando que é só educação.

**2. Ela confunde dois momentos diferentes**, que exigem perguntas diferentes.

---

## Os dois momentos, e por que separá-los muda tudo

### 🔧 Momento 1 — AJUSTE: ele já tem, e quer mudar

```
"não me manda mais o resumo de sábado"
"muda o horário do checklist para 7h"
"tira as renovações do meu briefing"
```

Aqui ele **já sabe** que o auxiliar existe: ele está ajustando. A única
ambiguidade real é temporal — e aí *"só desta vez ou sempre?"* é a pergunta
certa, curta e barata.

> **A pergunta existe para não gravar permanente o que era um pedido de hoje.**

### ✨ Momento 2 — OFERTA: ele não sabe que dá para automatizar

```
"me vê como estão as renovações que vencem esse mês"
"pesquisa o que mudou na regulação de auto"
"faz um resumo dos atendimentos de ontem"
```

Ele pediu **uma vez, avulso**. E talvez nem saiba que o sistema pode fazer isso
sozinho, toda semana, e mandar no canal que ele escolher.

> **Aqui a pergunta não é para confirmar. É para REVELAR uma capacidade.**

E é por isso que *"é sempre assim?"* falha: ela pressupõe que ele já sabe.

---

## A hierarquia da oferta — sempre nesta ordem

**Antes de propor construir qualquer coisa, olhe o que já existe.** Oferecer
criar algo que o catálogo já tem é a forma mais rápida de acumular três
auxiliares fazendo a mesma coisa.

```
1. JÁ EXISTE no catálogo, e ele NÃO ligou?
   → "O Primeira Mão faz exatamente isso, toda semana.
      Quer que eu ligue? Leva um clique."
   ✔ zero construção · ✔ ele descobre o catálogo · ✔ desligável na hora

2. JÁ EXISTE e ele JÁ LIGOU?
   → "Você já tem o Checklist das 6h. Quer que eu inclua isso nele,
      toda segunda?"
   ✔ não cria auxiliar novo · ✔ vira Rotina daquele Auxiliar

3. NÃO EXISTE nada que faça?
   → "Quer que eu automatize isso? Posso rodar toda segunda às 8h e
      te mandar por e-mail."
   ✔ só aqui se propõe construir
```

**A ontologia manda:** o que nasce em (2) e (3) é **Rotina de um Auxiliar** —
nunca uma Rotina solta, nunca um Auxiliar novo por conversa
([`ONTOLOGIA-DO-TRABALHO.md`](ONTOLOGIA-DO-TRABALHO.md), corolário 1).

---

## Quando oferecer — os gatilhos

**Um só basta. Nenhum deles é "achei que seria útil".**

| Gatilho | Como se sabe | Por que vale |
|---|---|---|
| **Repetição** | ele pediu a mesma coisa **≥ 2 vezes em 30 dias** | é o sinal mais forte que existe, e é medido, não deduzido |
| **Cadência no próprio pedido** | *"de ontem"*, *"deste mês"*, *"toda semana"* | a tarefa **já é** recorrente; ele só não sabe que dá para agendar |
| **O catálogo tem a resposta pronta** | existe Auxiliar `available` que faz aquilo | não é oferta de construção: é apresentação do que ele já pode ligar |

---

## Quando ficar quieto — e esta lista é mais importante

> **Uma oferta a mais é um incômodo. Uma oferta a menos é uma oportunidade
> perdida. Mas incômodo repetido faz o corretor parar de ler o que o sistema
> escreve — e aí ele perde todas.**

```
✗ é a PRIMEIRA vez que ele pede aquilo
     a primeira vez é para fazer o trabalho, não para vender automação

✗ ele já disse NÃO para aquele assunto
     o "não" é gravado e vale para sempre. Nunca se repergunta.

✗ já houve uma oferta nesta conversa
     no máximo UMA por conversa

✗ já houve mais de uma oferta nesta semana
     teto duro, mesmo com gatilho válido

✗ a tarefa é intrinsecamente única
     "qual a apólice do João?" não vira rotina

✗ ele está resolvendo um problema
     sinistro, cliente irritado, prazo estourando — não se vende no incêndio

✗ o pedido veio de um segurado, não do corretor
     atendimento não oferece automação a ninguém
```

---

## Como oferecer

**1. Depois do trabalho, nunca antes.** A oferta é rodapé. Ele pediu uma coisa;
entrega-se a coisa. Perguntar antes de responder transforma um pedido simples
num formulário.

**2. Uma linha, e não bloqueia.** Se ele ignorar, a conversa segue normal.

**3. Com padrão sugerido, aceitável numa palavra.**
Como o GPT Work faz: nunca três perguntas abertas. **Oferece um padrão e
aceita "pode".**

**4. Diz o ganho, não a mecânica.** Ele não quer saber o que é uma Rotina.

**5. E diz o que já sabe** — frequência, horário e canal já preenchidos com o
palpite mais provável, para ele só corrigir o que discordar.

### A copy

```
✗  "É sempre assim?"
      não diz o que está em jogo

✗  "Deseja criar uma rotina automatizada para esta tarefa?"
      fala a língua do sistema, não a do corretor

✗  "Posso automatizar isso?"
      automatizar o quê? com que frequência? para onde?

✓  "Você já me pediu isso 3 vezes este mês. Quer que eu faça sozinho
      toda segunda às 8h e te mande por e-mail?
      É só dizer 'pode' — e você desliga quando quiser."
```

**Os quatro elementos que a boa oferta sempre tem:**

```
1. POR QUE agora      "você já me pediu 3 vezes"
2. O QUE vai virar    "eu faço sozinho"
3. QUANDO e ONDE      "toda segunda às 8h, por e-mail"   ← já preenchido
4. COMO desfazer      "você desliga quando quiser"
```

O item 4 não é gentileza: **é o que torna o "pode" barato.** Quem sabe desligar
aceita experimentar.

---

## Depois do "pode"

```
1. cria a Rotina do Auxiliar — nunca um Auxiliar solto
2. confirma em UMA frase o que gravou, com horário e canal
3. mostra ONDE ver e desligar
4. e aparece imediatamente na página de Auxiliares — nada nasce escondido
```

**E o que nasce pelo chat pertence àquela corretora.** Promoção para o catálogo
global é decisão de admin, nunca do chat (SPEC-064 G.2.4).

---

## O "não" também é dado

Quando ele recusa, **registra-se o assunto recusado** — e aquele assunto nunca
mais é oferecido.

> Isso não é só educação: é a diferença entre um produto que aprende e um que
> insiste. Um sistema que repergunta o que já foi negado ensina o corretor a
> ignorar tudo que ele escreve.

E a recusa vira sinal de produto: **assunto muito oferecido e muito recusado é
oferta mal desenhada**, não corretor difícil.

---

## O que nunca pode acontecer

```
✗ oferecer na primeira vez que ele pede
✗ reperguntar um assunto já recusado
✗ criar Auxiliar ou Rotina sem o "pode" explícito
✗ criar Rotina sem Auxiliar dono
✗ criar algo global pelo chat
✗ oferta antes da entrega do trabalho
✗ oferta durante sinistro ou problema em curso
✗ mais de uma oferta por conversa
```

---

*Autoridade: CLAUDE.md · SPEC-064 Bloco F/G · decisão do Founder de 02/08/2026.*
