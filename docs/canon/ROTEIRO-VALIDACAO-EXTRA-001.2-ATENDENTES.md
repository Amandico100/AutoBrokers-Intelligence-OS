# Roteiro de validação com as atendentes — SPEC-EXTRA-001.2 · O agente lê tudo antes de falar

> **Quem conduz:** o Founder. **Quem prepara:** a execução da SPEC. ⛔ A execução não contata
> nenhuma das duas atendentes nem usa os números operacionais delas.
> **Quando:** depois do canário técnico (`ROTEIRO-CANARIO-EXTRA-001.2.md`) aprovado.
>
> 📊 O problema que esta SPEC ataca é o que as duas mais viram nos pilotos: o segurado escreve em
> pedaços e o agente respondia um por um (85,5% do que entra chega em rajada). O roteiro pede a elas
> o que **elas** fariam diante das mesmas rajadas — as perguntas, nunca os dados.

## Antes de começar (checklist do Founder)

- [ ] `smith-api` e `smith-web` implantados com o commit final da SPEC; canário técnico registrado no relatório §8.
- [ ] A atendente conversa com o agente pelo **TESTE-A** (nunca pelo número operacional dela) e olha o feed no painel.

## As perguntas (só elas respondem; anote a resposta literal)

| # | pergunta | o que a resposta decide |
|---|---|---|
| 1 | Mande 4 ou 5 mensagens seguidas, como um cliente apressado. A resposta veio **inteira e uma vez só**? Ela respondeu a **tudo** que você mandou? | o turno (A). Uma resposta por mensagem é blocker. |
| 2 | Mande fotos em sequência (3 ou mais). Ele respondeu **uma vez** e citou as fotos? | mídia no buffer (B). |
| 3 | A resposta é **curta e humana** ou virou textão? Você mandaria assim para o cliente? Se dividiu em duas, fez sentido? | classe de tamanho (F). 💭 Régua humana medida: 1–2 mensagens, ~90 caracteres. |
| 4 | Ele **repetiu alguma pergunta** que você já tinha respondido (placa, CPF, endereço)? | a ficha (C). Qualquer repetição é achado. |
| 5 | Ele **se apresentou na hora certa** (só na abertura)? Cumprimentou no meio da conversa? Quando você voltou depois de encerrar, ele se reapresentou? | apresentação e reencontro (D). |
| 6 | O "digitando…" ajuda ou incomoda? Apareceu quando **você** estava atendendo a conversa? | presença (B). Se apareceu com ela atendendo, é blocker. |
| 7 | O **nome** do agente está certo? Quando ele disse "vou passar para a especialista", nomeou a pessoa **certa** (ou ninguém)? Alguma vez pareceu que a "especialista" era ele mesmo? | o nome (§10). |
| 8 | Quando você respondeu pelo celular e o agente calou, o **feed** explicou por quê de um jeito que você entende? | o silêncio com motivo (E). |

## Como registrar

Uma linha por pergunta, com a resposta literal e a data, em
`docs/canon/reports/SPEC-EXTRA-001.2-EXECUTION-REPORT.md` §8.2 ("validado pela atendente").
⛔ Não declarar aceite antes de recebê-lo; não travar o trabalho técnico esperando a agenda delas.
