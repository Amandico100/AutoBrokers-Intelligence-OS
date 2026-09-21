# As 15 perguntas para a atendente da corretora — portal de vidros

> **Para quem é:** a atendente que abre os acionamentos de vidro no portal — e o Founder lê junto.
> **Para que serve:** medimos o portal por dentro (📊 5 capturas de tráfego, 20/09/2026) e sabemos o que ele
> **faz**. O que não dá para medir é **o que acontece depois**, fora da tela: quem liga para quem, o que o
> segurado reclama, o que você faz quando algo não encaixa. É isso que estas perguntas buscam.
> **v1.0 · 21/09/2026** · nasceu no fecho da SPEC-EXTRA-001.10.

---

## Como responder

**Não precisa escrever bonito.** Frase curta serve. "Nunca vi isso acontecer" é uma resposta ótima — e às
vezes é a mais valiosa de todas, porque desmente uma suposição nossa.

Se a resposta for **"depende da seguradora"**, diga **de quais** você lembra. Essa é a informação que mais falta.

🔴 **Nunca escreva aqui:** CPF, placa, nome de segurado, telefone, e-mail ou número de apólice/atendimento.
Se precisar dar um exemplo, diga "um caso de para-brisa na seguradora X".

---

## 1 · Quando o portal abre a agenda, e quando ele manda direto para a loja

**A pergunta:** às vezes o portal deixa você escolher a loja, o dia e o horário; outras vezes ele já fecha com
uma loja e diz para ligar lá. **Você consegue prever qual dos dois vai acontecer, antes de chegar no fim?**
E se consegue: o que faz a diferença?

📊 **O que medimos:** para-brisa com **reparo aceito** → fechou com loja, sem agenda. **Lataria** → fechou com
loja, sem agenda. **Vidro de porta (troca)** → abriu agenda, com uma loja. Mesma seguradora, mesma apólice.
**Confirme se isso bate com a sua experiência:** reparo e lataria sempre fecham direto na loja?

**O que muda no robô:** hoje ele **pergunta ao portal** e lê a resposta, sem adivinhar. Se você souber a regra,
ele passa a **avisar o segurado antes** o que vai acontecer — e isso muda a conversa inteira.

---

## 2 · Depois que o portal fecha direto com a loja: quem liga para quem, e em quanto tempo?

**A pergunta:** a tela diz "entre em contato com a loja para agendar". **Na prática, quem liga primeiro?**
A loja liga para o segurado? Para a corretora? Ou é o segurado que tem de ligar para a loja?
E **quanto tempo** costuma levar até alguém se falar — horas, um dia, mais?

**O que muda no robô:** é o que ele promete ao segurado no fim. Se hoje ele diz "a loja vai entrar em contato"
e na verdade é o segurado que tem de ligar, ele está prometendo o que não acontece.

---

## 3 · O contato: você põe o telefone e o e-mail de quem, e por quê?

**A pergunta:** na tela de dados, você preenche telefone e e-mail. **De quem você põe?** Seu? Da corretora?
Do segurado? **E por que você faz assim** — é regra da casa, é o que dá menos problema, ou nunca pensou nisso?

📊 **O que medimos:** em **3 de 4** capturas foi gravado o telefone como **"celular do corretor"**, e o portal
marcou que **o segurado não recebe aviso nenhum**. Existe um tipo "celular do segurado" que **nunca** foi usado.

---

## 4 · Você já viu o segurado receber WhatsApp ou SMS do portal?

**A pergunta:** o portal diz que manda atualizações por e-mail ou SMS. **Algum segurado já te falou que
recebeu?** Ou eles sempre perguntam tudo para você?

**E o que você acha que aconteceria** se puséssemos o **celular do segurado** no lugar do da corretora:
ele passaria a receber? Isso ajudaria ou ia confundir (ele recebendo do portal e do nosso agente ao mesmo tempo)?

**O que muda no robô:** é a decisão D-E00110-F1, que está esperando justamente esta resposta.

---

## 5 · "Relação com o titular": o que você escolhe, e muda alguma coisa?

**A pergunta:** tem uma lista com *O próprio · Cônjuge · Filho · Corretor · Outros*. **Qual você marca?**
E **muda alguma coisa** no que acontece depois — quem recebe o e-mail, quem a loja procura?

📊 **O que medimos:** nas 4 capturas apareceram **três respostas diferentes** (O próprio, Corretor, Outros).
Não parece ter critério fixo — e isso pode ser justamente o ponto.

---

## 6 · O e-mail da corretora recebe cópia de quê, exatamente?

**A pergunta:** chega alguma coisa na caixa de e-mail da corretora depois do acionamento? **O quê** — o
comprovante, o agendamento, a conclusão do serviço, nada? E isso é útil, ou vira lixo na caixa?

**O que muda no robô:** se o e-mail é a única prova que sobra do atendimento, ele precisa garantir que ela chega.

---

## 7 · Quando a peça não aparece na lista, ou aparecem duas parecidas

**A pergunta:** o segurado descreve a peça e você vai procurar na lista do portal. **O que você faz quando
não acha?** E quando aparecem **duas parecidas** ("vidro de porta" e "vidro de janela", por exemplo): **como
você decide?** Já errou alguma vez e descobriu depois?

**O que muda no robô:** ele agora **recusa** escolher uma peça que não bate exatamente com o que o segurado
disse, e para para perguntar. Se você tem um critério que funciona, ele aprende o critério em vez de parar.

---

## 8 · Quando a causa do dano não encaixa em nenhuma das opções

**A pergunta:** o portal dá uma lista de causas ("como ocorreu o dano"), e ela **muda conforme a peça**.
**O que você faz quando nada na lista descreve o que o segurado contou?** Escolhe a mais parecida?
Escolhe uma genérica? Liga para alguém?

**E uma pergunta de honestidade:** escolher a causa "mais ou menos certa" já deu problema depois?

---

## 9 · Reparo × troca: o segurado pode recusar o reparo? E se o reparo não ficar bom?

**A pergunta:** quando a trinca é pequena, o portal oferece **reparo** em vez de trocar o vidro (grátis, uns
30 minutos). **O segurado pode dizer que não quer e exigir a troca?** O que acontece se ele recusar?

**E depois:** se o reparo **não ficar bom**, dá para voltar e pedir a troca? Abre um atendimento novo?
Paga franquia de novo?

📊 **O que medimos:** no para-brisa, o portal mostrou **três valores** — valor para troca, desconto para reparo,
e valor para reparo **sem franquia**. O robô hoje pergunta ao segurado, **antes** de abrir o pedido, se ele
aceita tentar o reparo. Queremos saber se essa pergunta está certa, e se a resposta pode ser mudada depois.

---

## 10 · Quando o portal pede fotos ou vistoria, o que você faz?

**A pergunta:** já aconteceu de o portal pedir **vistoria** ou **fotos**? **Em qual seguradora, e em que peça?**
E como você envia as fotos — por um link que o portal manda, por WhatsApp, por e-mail? **Quem tira as fotos:**
o segurado, e você repassa?

📊 **O que medimos:** o portal tem um caminho inteiro de vistoria que **nunca apareceu** nas capturas. O robô
o reconhece e **para**, porque não sabe o que vem depois.

---

## 11 · Atendimento a domicílio: quando o portal oferece, e cobra alguma coisa?

**A pergunta:** já apareceu a opção de o técnico **ir até o segurado** em vez de ele levar o carro à loja?
**Em que cidades** isso costuma aparecer? **Cobra a mais?** O segurado prefere?

**E quando a cidade do segurado não tem loja nenhuma:** o que você faz hoje? Manda para a cidade vizinha?
Pede reembolso? Explica que não dá?

---

## 12 · 🔴 Dá para RETOMAR um atendimento parado? Por onde?

**A pergunta mais importante da lista.** Imagine que você abriu o atendimento, pegou o número, e aí teve de
parar no meio (o segurado sumiu, faltou um dado, deu erro na tela). **Mais tarde, dá para voltar naquele mesmo
atendimento e continuar de onde parou?**

- **Por onde?** Tem um "Consultar atendimento" na primeira tela — **é por ali?**
- **O que ele pede** para achar o atendimento: o número? o CPF? a placa?
- **Dá para continuar de verdade**, ou ele só mostra o status e você tem de começar tudo de novo?

🔴 **Por que importa tanto:** hoje o robô abre o pedido e, se qualquer coisa der errado depois disso, ele
**não consegue voltar** — o acesso dele ao atendimento se perde. Toda parada vira trabalho manual seu.
**A sua resposta decide sozinha** o desenho da próxima entrega (a SPEC-EXTRA-001.10.1).

---

## 13 · Cancelar: quais motivos existem, e qual você usa para "abri por engano"?

**A pergunta:** quando você cancela um atendimento, o portal pede um **motivo**, de uma lista.
**Quais motivos tem nessa lista?** (Se der, tire um print dela aberta — sem cancelar nada.)
**Qual você usa** quando o atendimento foi aberto por engano, ou quando o segurado desistiu?

📊 **O que medimos:** o robô conhece **um** código de motivo, tirado do programa do portal, e **nunca viu a
lista**. Cancelar com o motivo errado deixa registrado na seguradora uma razão que não é a verdadeira.

---

## 14 · O que você percebe de DIFERENTE entre as seguradoras?

**A pergunta:** pensando em **Porto, Azul, Tokio, HDI, Allianz e Bradesco** — o que muda de uma para outra?
Por exemplo:

- alguma pede coisa a mais logo no começo (escolher a cobertura, por exemplo)?
- alguma tem perguntas que as outras não têm?
- alguma costuma dar erro, ou não achar a apólice?
- alguma abre agenda mais do que as outras?
- **a Bradesco usa este mesmo portal, ou outro sistema?**

📊 **O que medimos:** o portal publica **38** seguradoras e nós só capturamos **duas** (Yelum e Porto). O robô
já sabe abrir o pedido em todas, mas o que cada uma **pergunta** é desconhecido.

---

## 15 · Livre escolha de oficina, e as dúvidas que sobram depois

**A parte A:** quando o segurado pergunta *"posso levar na minha oficina?"* — **como isso aparece no portal?**
Tem alguma tela ou aviso dizendo que ele tem direito a escolher? Ou você responde de cabeça, pela apólice?

**A parte B:** depois que o atendimento é aberto, quais são as **dúvidas que mais voltam**? Confira se estas
quatro respostas, que já saíram de você, valem para **todas** as seguradoras ou só para algumas:

```
1. "A loja vai entrar em contato para vistoria ou para agendar; se o orçamento passar do limite,
    a central liga."
2. "Peça padrão abre agenda para troca."
3. "Posso indicar oficina? Na rede referenciada, não. Com livre escolha contratada, pode."
4. "As peças são genuínas do fabricante, sem logomarca; pequenos reparos são sempre indicados pela
    seguradora; e não há reembolso sem autorização prévia."
```

**Para cada uma:** vale para todas? Vale só para algumas (quais)? Ou tem exceção que você já viu?

---

## O que acontece com as respostas

Cada uma vira um pedaço do que o robô fala com o segurado, ou uma trava que o impede de fazer besteira.
Três delas mexem em decisões que ainda estão abertas: a **nº 4** (o contato do segurado), a **nº 12** (a
retomada — decide a próxima entrega) e a **nº 13** (o motivo de cancelamento).

**Nada aqui é teste.** Se a resposta for "nunca vi", escreva "nunca vi". Saber que algo nunca acontece vale
tanto quanto saber como acontece.
