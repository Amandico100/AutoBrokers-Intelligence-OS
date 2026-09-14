# Roteiro de validação com as atendentes — SPEC-EXTRA-001.1 · A apólice certa, inteira, em uma rodada

> **Quem conduz:** o Founder. **Quem prepara:** a execução da SPEC. ⛔ A execução não contata
> nenhuma das duas atendentes nem usa os números operacionais delas.
> **Quando:** depois do canário técnico (`ROTEIRO-CANARIO-EXTRA-001.1.md`) aprovado.
>
> 📊 A atendente da Resulta é a dona do caso de referência (a HDI residencial com 10 coberturas e a
> Allianz condomínio com 21). O roteiro pede a ela exatamente as perguntas que ela fez nos pilotos
> de 09–11/09 — **as perguntas, nunca os dados**.

## Antes de começar (checklist do Founder)

- [ ] `smith-api` e `smith-web` implantados com o commit final da SPEC; canário técnico registrado no relatório §7.
- [ ] A atendente usa o chat `core` do painel com a conta dela, na carteira dela.

## As perguntas (só elas respondem; anote a resposta literal)

| # | pergunta | o que a resposta decide |
|---|---|---|
| 1 | Pergunte pela apólice de um cliente **só pelo CPF**. Veio **a apólice certa** (a vigente), sem lista? | BLOCO B (vigência na porta). Se veio lista com vencidas, é blocker. |
| 2 | Peça as coberturas da **residencial da HDI** daquele cliente. Veio **inteira** — as 10 linhas, com as assistências? | BLOCO A/D (reconciliação + extrator). 💭 Esperado: 10; antes eram 6. |
| 3 | Dá para ver **de onde cada número saiu** (cadastro da corretora × documento da apólice)? Isso ajuda ou atrapalha? | origem por linha (A/C). Se atrapalha, vira ajuste de redação, não de dado. |
| 4 | Na franquia de Danos Elétricos, a resposta mostrou **dois valores** (o do cadastro e o do documento). Você prefere ver os dois, ou só o do documento com um aviso? | D-PILOTO-11 (divergência mostra as duas). A preferência dela alimenta a redação. |
| 5 | Quando o robô **perguntou "qual apólice?"**, fazia sentido (duas vigentes do mesmo ramo)? Ou ele perguntou sem precisar? | BLOCO B (M-B2). Qualquer "perguntou sem precisar" é achado. |
| 6 | Num cliente **sem apólice vigente**, a frase "a última vigente foi a X, que valeu até dd/mm" é entendível? Você diria assim para o cliente? | §6.2. |
| 7 | A forma de pagamento que apareceu (cartão × boleto) bate com o que o cliente **paga de verdade**? | `forma_pag` do cabeçalho × parcelas (D). |
| 8 | Na conversa de WhatsApp de um cliente que diz "meu carro quebrou" e manda o CPF depois, o robô foi para a apólice **de auto** sem perguntar? | BLOCO B (M-B3). |

## Como registrar

Uma linha por pergunta, com a resposta literal e a data, em
`docs/canon/reports/SPEC-EXTRA-001.1-EXECUTION-REPORT.md` §7.2 ("validado pela atendente").
⛔ Não declarar aceite antes de recebê-lo; não travar o trabalho técnico esperando a agenda delas.
