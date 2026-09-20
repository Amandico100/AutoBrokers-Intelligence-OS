# PROMPT DO VEREDITO DO PILOTO — para colar num chat novo, no 4º dia

> **Como usar:** abra um chat novo (Claude Code, na árvore `AutoBrokers-FIX`), troque **as duas datas**
> da primeira linha pelos 3 dias úteis do piloto, e cole tudo o que está entre as linhas `---`.
> Nada aqui envia mensagem, liga agente ou escreve no banco.

---

Você é o JUIZ DO PILOTO da EXTRA-001.7. O piloto rodou de **DD/MM/AAAA a DD/MM/AAAA** (3 dias úteis, agente
ligado nas corretoras do piloto). Sua tarefa é dar um veredito **PASSOU / NÃO PASSOU**, em pt-BR, linguagem
de gente — o leitor é o Founder, não é programador.

⛔ **Regras invioláveis desta tarefa:**
- Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`. Não edite código. Não commite.
- Banco: **só SELECT**. Nenhuma escrita, nenhuma mensagem sai, nenhum agente é ligado ou desligado.
- **PII nunca sai**: em nenhum SELECT seu apareça nome, telefone, CPF, placa, número de apólice ou
  endereço no resultado impresso. Para avaliar o texto das conversas, leia o conteúdo **em memória** e
  **reporte só a classificação e um trecho de no máximo 8 palavras sem dado identificável** — ou,
  preferindo, nem o trecho.
- Separe **FATO** (📊 medido, com o comando ao lado), **INFERÊNCIA** e **RECOMENDAÇÃO**.
  Número sem marca é defeito.
- Leitura que falha **nunca vira zero**: escreva "NÃO LIDO" e repita a leitura uma vez.

## Faça, nesta ordem

**1 · O checklist de ligar.** Rode, da sua máquina, contra a produção:
```
cd backend && python scripts/conferir_o_que_esta_no_ar.py --ligar
```
Ele diz PODE LIGAR / NÃO PODE LIGAR, com uma linha por trava. Se quebrar com `ModuleNotFoundError:
portal_worker`, diga isso e siga — é um defeito conhecido do console, não do piloto.
**Reporte:** o estado das travas **durante** o piloto, e se alguma delas invalida os 3 dias (por exemplo,
`ATTENDANT_INBOUND_ALLOWLIST` preenchida — isso faria o piloto medir o vazio, e o veredito é
**INVÁLIDO**, não "não passou").

**2 · A medição do período.**
```
cd backend && python scripts/medir_o_piloto.py --de AAAA-MM-DD --ate AAAA-MM-DD --formato markdown
```
Use as datas do piloto (a última é **inclusive** e deve ser um dia **fechado**, nunca hoje).
**Reporte** a tabela por corretora e a régua: cada dimensão com a nota, o critério ao lado e o palpite
antigo de 12/09 para comparar. Respeite o que o script diz: "NÃO AVALIADA — amostra insuficiente",
"NÃO MENSURÁVEL" e "NÃO LIDO" são respostas honestas e não devem ser transformadas em nota.

**3 · O avaliador por amostra** — as três notas que o produto **não grava** (P-E0017-03, decisão
D-E0017-04, opção C). Você é o avaliador: **um agente do plano lendo as conversas**, nunca a API do
produto, nunca um proxy por SELECT.

- Monte a amostra por SELECT, no período do piloto, nas corretoras do piloto: as conversas em que o
  **agente falou** (e não só observou). Alvo: **10 conversas por corretora por dia de piloto**, ou
  todas, se forem menos. Se a amostra total ficar **abaixo de 15 conversas**, diga isso e marque as três
  notas como **NÃO AVALIADA — amostra insuficiente**.
- Leia o texto de cada conversa **sem imprimir PII**. Para cada uma, classifique:

| dimensão | pergunta | escala |
|---|---|---|
| **fala como humano** | soou como gente, ou soou robô/formulário? | sim · mais ou menos · não |
| **sabe calar** | ele devia ter falado e calou, ou devia ter calado e falou? | não (agiu certo) · sim, falou demais · sim, calou demais |
| **apólice certa de primeira** | a apólice que ele usou era a certa, **na primeira rodada**? | sim · precisou corrigir · errou · não se aplica (conversa sem apólice) |

- Converta em nota 0–100 por dimensão, dizendo **a conta que você usou** (ex.: `sim=100, mais ou
  menos=50, não=0`, média sobre as conversas avaliáveis). **Escreva a conta.**
- Reporte também, em número: quantas conversas na amostra, quantas de cada corretora, quantas
  descartadas e por quê.

**4 · O veredito.** O piloto **PASSOU** se, **em cada corretora do piloto**, as quatro linhas abaixo forem
verdadeiras:

```
① nenhuma dimensão MEDIDA ficou abaixo do palpite de 12/09
② "aciona" ............. pelo menos 5 casos E nota ≥ 70
③ "sabe pedir ajuda" ... ≥ 90
④ apólice errada ....... no máximo 1 em cada 10 da amostra
```

- Dimensão **NÃO AVALIADA** não reprova e não aprova: ela sai como "sem resposta", e você diz **o que
  falta** para ela ter resposta da próxima vez.
- Uma corretora com dado e a outra sem → veredito **por corretora**, e diga isso claramente.
- 💭 Esses quatro cortes são proposta, não lei: a decisão **D-E0017-03** é do Founder e está aberta. Diga
  isso ao fim, numa linha.

## Como responder (≤ 40 linhas)

```
VEREDITO: PASSOU / NÃO PASSOU / INVÁLIDO  — por corretora, com uma frase de porquê
📊 a tabela do período (corretora × dia): conversas, rajadas, acionamentos, handoffs, silêncios
📊 a régua: nota por dimensão, com o critério e o palpite de 12/09 ao lado
📊 as três notas do avaliador, com o tamanho da amostra e a conta usada
os quatro cortes, um a um: bateu / não bateu / sem resposta
o que ficou NÃO AVALIADA e o que falta para medir da próxima vez
o que você recomenda fazer a seguir — no máximo 3 itens, em ordem
```

Nada de PII. Nada de escrita. Se algo impedir a medição, diga **o que** impediu e **o que o Founder faz
para destravar** — não invente número.

---
