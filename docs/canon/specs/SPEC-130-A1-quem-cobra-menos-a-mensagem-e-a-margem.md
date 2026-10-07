# SPEC-130-A.1 — Quem Cobra Menos: a mensagem, o mínimo do mínimo e a margem corrigida

> v1.0 · 06/10/2026 23h · gerente Opus 5.5 · branch `spec/130-A1-quem-cobra-menos` · base `705b67f` (main)
> Origem: o retorno do Founder depois da entrega da SPEC-130-A (06/10, noite). Ele liberou: *"o que for da SPEC 130-A e
> você quiser executar e ajustar baseado no que eu falei, você está liberado"*. A página do canal fica para depois
> (*"vamos fazer grandes mudanças depois por serviço… agora só mudar a mensagem do WhatsApp"*).

## 1. EXECUTION CARD
```
OUTCOME ..............  o pedido do CANAL (Quem Cobra Menos) sai com a mensagem de WhatsApp de comparador ao consumidor —
                        o vencedor em destaque, o volume real de cotações, o tempo, a economia, 2 cartões, o melhor preço
                        por seguradora (6) e quem é a corretora — e com um 4º cálculo, o "mínimo do mínimo", que mostra a
                        maior economia possível sem nunca virar a recomendada. A margem passa a descer até o piso SEM
                        aprovação humana, passo a passo, com os últimos ~2 pp guardados como alavanca de fechamento em R$.
                        A proposta da CARTEIRA (renovação/cotação) continua a da 130-A e não fala de Quem Cobra Menos.
RISCO ................  6 — ALCANCE 3 (o consumidor lê) · REVERSIBILIDADE 2 (migration de constraint) · FREQUÊNCIA 1
SUPERFÍCIE ...........  1 — peças da 130-A e da 129-B que já existem
PISO APLICADO ........  §3.2 — migration (constraint, expand-only) · texto ao consumidor com número (honestidade/CDC)
NÍVEL ................  🟠 ALTO · gerente Opus 5.5 · 3 builders Opus 5.5 xhigh em PARALELO · juiz ‖ red team
O FIO ................  porta (opção `minima` aceita) → motor (4º cálculo no mesmo negócio) → comparacao (papel `minima`)
                        → proposta.montar (resumo: cotações reais, tempo, economia; opção mínima no modelo do canal)
                        → mensagem.mensagem_do_canal(modelo, link) → comando_proposta escolhe pela ORIGEM do pedido
                        · teste do fio: o pedido real do canário (d0bb15ba, origem canal) → os balões do canal; o mesmo
                        modelo com origem corretora → a mensagem da 130-A, sem "Quem Cobra Menos"
PARALELISMO REAL .....  F1 (margem: negociacao + manual + porta.cotacao_alvo) ‖ F2 (a mensagem do canal: mensagem +
                        proposta + comando) ‖ F3 (o mínimo: presets + motor + porta.OPCOES + migration + comparacao)
                        — F1 e F3 tocam porta.py em funções DIFERENTES: F3 só a tupla OPCOES; F1 só cotacao_alvo e cia.
UNIDADES .............  U1 margem corrigida (D-MC-68) · U2 manual por contexto (carteira × canal) · U3 mensagem do canal
                        · U4 resumo real (cotações, tempo, economia) · U5 preset mínimo + constraint · U6 papel `minima`
                        · U7 tirar a remuneração CNSP (D-130A-08 revogada)
COESÃO ...............  U1+U2 (o manual descreve a régua que a negociação aplica) · U3+U4+U7 (a mensagem lê o resumo do
                        modelo) · U5+U6 (o cálculo e quem o lê)
TIME .................  gerente · F1 · F2 · F3 · juiz ‖ red team · conserto único
REFERÊNCIA ...........  `docs/canon/specs/SPEC-130-A-a-comparacao-e-a-proposta.md` · o print do Founder (06/10) · o logo
                        do Quem Cobra Menos (só para a página futura)
GATES ................  §4
O ELO ................  "o número de cotações que o consumidor lê é o número de preços que voltaram": o teste afirma a
                        contagem do modelo contra as ofertas do pedido, nunca contra uma fórmula
FAIXA DE RELÓGIO .....  💭 3–4 h
```

## 2. As decisões (o Founder pediu: decidir pela maior nota e avisar no fim — sem parar para perguntar)

| id | decisão | opções e notas |
|---|---|---|
| **D-MC-68 (corrigida)** | o agente desce até o piso (10 %) **sozinho**, sem aprovação humana, **passo a passo** (1 pp por vez); de 15 → 12 % é a negociação normal; 12 → 10 % é a **alavanca de fechamento**: guardada para o fim, oferecida **em reais** ("a seguradora devolveu R$ X a menos no recálculo"), **condicionada ao fechamento**, nunca em "%" | como o Founder disse **95** · como estava gravado (10 % só com o corretor aprovando) **20** — gravado errado |
| **D-130A-08 (revogada)** | a remuneração CNSP 382 sai do produto: *"nós não vendemos seguros; nós só informamos através da tecnologia"*. Sai a chave da config, o campo do modelo e a T-127 | tirar **92** · manter desligado **40** |
| **D-130A1-01** | a mensagem do CANAL é outra função (`mensagem_do_canal`), escolhida pela **origem** do pedido; a da carteira continua a da 130-A, sem nenhuma menção ao Quem Cobra Menos | duas funções **93** · uma função com chave **70** |
| **D-130A1-02** | **"Cotações realizadas" = o número REAL de preços que voltaram** (todas as ofertas das OPÇÕES do pedido, de todas as corretoras — nunca os recálculos da negociação). 📊 o canário de 05/10 teve 82 preços nas opções (38 padrão + 44 econômica; o juiz e o red team pegaram que os 22 do recálculo entravam na conta — conserto) — já é o volume que o Founder quer mostrar, e cresce sozinho a cada corretora nova. A fórmula "seguradoras × 3 × corretoras + 100" **não** entra: o +100 é um número que não aconteceu, dito a um consumidor (CDC art. 37 — publicidade enganosa; art. 67 tipifica). Num produto que vende **confiança** ("só aceite Nível 5"), um print de "190" com 90 preços reais custa a marca inteira no Reclame Aqui | número real **90** · fórmula sem o +100 (seguradoras × cálculos × corretoras, que pode contar cálculo recusado) **60** · fórmula do Founder **25** |
| **D-130A1-03** | **"Você economiza até R$ X"** = a mais cara com a mesma cobertura completa − a mais barata mostrada (a mínima, se houver), com a frase dizendo de onde vem a conta. Contra o preço ATUAL só quando houver apólice lida | assim **88** · só contra a mais cara da completa **75** · sem a frase de origem **30** |
| **D-130A1-04** | **"Corretora Nível 5"** é o selo do programa (config `canal.selo`), ligado por padrão para quem entra no canal; a lista do Nível 5 é pública na página do Quem Cobra Menos (SPEC da página). Antes de escalar, a lista tem de existir escrita — senão o selo vira promessa sem critério | selo do programa com lista **85** · selo sem lista **45** |
| **D-130A1-05** | o **"mínimo do mínimo"** é um 4º cálculo (`minima`) = a econômica **sem carro reserva** (📊 `carroReserva: 0` pedido ↔ "Não contratar" em 90 de 90 ofertas de 13 seguradoras, `vivo_conta_b.json` — cruzado pela F3; ⚠️ "Não"/"Não desejo contratar" vêm de pedidos com código 2, são produtos sem carro reserva; 📊 efeito medido no menor preço: −0,3 % a −6,9 % em 10 de 13 seguradoras), com a comissão NORMAL. Vidros ficam no básico (📊 sem vidros a Allianz recusa) e terceiros intactos (📊 com RCF 0 Bradesco e Aliro recusaram). Franquia "majorada" não entra: o código 4 aparece no acervo, mas o rótulo não foi medido (§9.5). Só o canal pede o `minima` (a carteira não gasta 1 cálculo a mais por corretora) | assim **86** · com franquia 4 sem medir **35** · sem o 4º cálculo **50** |
| **D-130A1-06** | a mensagem termina com **uma pergunta** (abre a conversa e a janela do WhatsApp); sem resposta, **até 2 lembretes** (💭 15 min e no dia seguinte, em horário comercial — config `canal.follow_up`). Quem envia é a 133-A | pergunta + 2 lembretes **88** · só pergunta **72** · lembretes sem pergunta **55** |
| **D-130A1-07** | o manual de negociação ganha **contexto**: `carteira` (renovação e cotação de quem já é cliente — tom de quem conhece) e `canal` (consumidor frio do Quem Cobra Menos — prova, volume e o vencedor primeiro; a corretora entra como "quem atende"). A régua de margem é a mesma | por contexto **90** · um só manual **55** |

## 3. A mensagem do canal (o que o consumidor lê)

💭 ilustrativo, com os números do canário de 05/10 — a forma, não o texto final (o builder escreve com os dados do modelo):

```
balão 1   *Quem Cobra Menos no seu seguro auto foi encontrado* 🏆
          Vencedor em *82 cotações* entre 2 corretoras e 13 seguradoras.

          Cotações realizadas: *82*
          Tempo: *47 segundos*
          Você economiza até *R$ 2.585* por ano _(da mais cara para a mais em conta com a mesma proteção)_

          *Quem cobra menos?*
          Corretora AutoFleet com a Youse
          *12x de R$ 345,82* com juros, total R$ 4.149
          ou *R$ 3.730,56* à vista · até 6x sem juros

balão 2   *Recomendada* · nota 87
          Youse · *R$ 3.730,56/ano* · franquia R$ 4.120
          Batida, roubo, terceiros R$ 200 mil, carro reserva 15 dias

          *Mais em conta* · nota 78
          Youse · *R$ 2.975,96/ano*
          _Cobre menos: sem carro reserva, franquia normal e vidros básicos._

          *Melhor preço por seguradora*
          Youse R$ 3.730 · HDI R$ 4.010 · … (6)
          _Lista completa no link abaixo._

balão 3   *Quem é a corretora que cobra menos?*
          AutoFleet
          Corretora Nível 5
          Google: 5,0 (14 avaliações)
          SUSEP: 202xxxxxx
          17 anos de mercado

          _Atenção: só aceite corretoras Nível 5._
          <link — a página com as 3 opções lado a lado, a lista inteira e como acionar o seguro>
          Os preços valem até 11/10/2026.
          Quer que a AutoFleet reserve esse preço para você?
```

Regras: só dado do modelo (nada inventado); linha sem dado some (sem Google, sem SUSEP, sem anos → a linha não aparece); juros
com nome e total; "sem juros" só quando é verdade; a mais em conta diz o que deixa de cobrir; nada de "o mais barato do mercado",
cronômetro ou urgência; comissão nunca; a corretora que perdeu nunca com nome. ≤ 3 balões; ≤ 3 emojis no total.

## 4. Gates
G1 bateria das peças da 130-A + 129-B verde · G2 `mensagem_do_canal`: contagem = ofertas reais (o guarda fica VERMELHO com a
fórmula +100 reintroduzida) · G3 a mensagem da carteira não contém "Quem Cobra Menos" nem "Nível 5" · G4 linha sem dado some ·
G5 negociação: desce 1 pp por vez; 12→10 sem `aprovado_pelo_corretor`; nunca abaixo do piso; a alavanca de fechamento sai em R$ e
nunca com "%" · G6 `minima`: preset = econômica + `carroReserva 0`, a porta aceita, o motor ordena por último antes do ajuste,
a constraint aceita e recusa o desconhecido (VERIFY com controle) · G7 `minima` nunca é a recomendada nem entra no ranking da
completa · G8 nenhum número comercial fora da config · G9 nenhuma `remuneracao` no modelo · `npm run test:rotas-montam` se tocar
`app/` (não deve).

## 5. Fora desta SPEC (planejado)
- **A página do Quem Cobra Menos** (marca própria — o "Q" azul-marinho com a cauda verde-limão —, a corretora vencedora DENTRO,
  o bloco "Corretora Nível 5" com a lista, a lista completa por seguradora): SPEC própria **130-B-QCM**, antes de abrir o canal ao
  público. Não substitui a página da carteira (a da 130-A), que segue sem nenhuma menção ao Quem Cobra Menos.
- O envio, o número do canal (temporário **47 98808-7463**), o pareamento e os lembretes: **133-A**.
- Comerciais com WhatsApp e Agger próprios e o produtor/indicador/fechador do InfoCap: plano em
  `docs/canon/programa-multicalculo/PLANO-COMERCIAIS-E-CONTAS.md` (construção depois da 131).
