# Roteiro de validação com as atendentes — SPEC-EXTRA-001.6 · A cobrança prova que funciona

> **Quem conduz:** o Founder. **Quem prepara:** a execução da SPEC. ⛔ A execução não contata
> nenhuma das duas atendentes nem usa os números operacionais delas.
> **Quando:** depois da Implantação 2 (B1–B4 no ar), com a rotina da Resulta em modo
> **Encaminhar para minha equipe** e o WhatsApp da equipe = **TESTE-B** durante o canário.
>
> O relatório da SPEC distingue três estados e este roteiro alimenta o terceiro:
> **não testado** · **aprovado no canário técnico** · **validado pela atendente**.

## Antes de começar (checklist do Founder)

- [ ] `smith-api`, `smith-web` e `portal-worker` implantados com o commit final da SPEC.
- [ ] Migrations `20260914_01` e `20260914_03` aplicadas e verificadas (relatório §4).
- [ ] Na tela do Auxiliar de cobrança da Resulta: **"Quem assina a mensagem"** preenchido com o
      nome da atendente · modo **Encaminhar para minha equipe** · **WhatsApp da equipe = TESTE-B** ·
      **Dias entre cobranças do mesmo segurado = 7**.
- [ ] Rotina reativada **só depois** disso (D-PILOTO-18).
- [ ] Uma execução real concluída; o pacote chegou em TESTE-B.

## As perguntas (só elas respondem; anote a resposta literal)

| # | pergunta | o que a resposta decide |
|---|---|---|
| 1 | A mensagem chegou **inteira**? Dá para encaminhar ao cliente sem editar nada? | P0.1 (bloco único). Se veio picotada, é blocker. |
| 2 | A **nota interna** diz de quem é a cobrança (cliente, seguradora, parcelas, valor, WhatsApp) sem você precisar abrir o painel? | o conteúdo da nota (`_nota_interna_para_a_equipe`) |
| 3 | Quando o mesmo cliente tem 3 boletos, **uma** mensagem com 3 PDFs é melhor do que 3 mensagens? | B1.2 (agrupar por segurado). 💭 A resposta esperada é sim — se não for, a copy do plural (B1.5) muda. |
| 4 | O **nome que assina** a mensagem é o certo? É assim que você se apresenta ao cliente? | P0.4 (`attendant_name`) |
| 5 | Quando um portal **não entra**, o que você lê no relatório basta para saber **o que fazer**? (ex.: "senha recusada — atualize em Conectores > Portais") | P0.2, B2/B3 (motivo e `health` em português) |
| 6 | No relatório da execução, você prefere ver o **CPF inteiro** ou só os **4 últimos dígitos**? | B4.4 (a máscara do relatório). A nota interna continua com o WhatsApp legível de qualquer forma. |
| 7 | O mesmo cliente foi cobrado **de novo** em menos de 7 dias em algum momento? | B1.3 (janela por segurado). Qualquer "sim" é blocker. |
| 8 | Alguma parcela chegou **duas vezes**? | B1.1 (dedup sempre). Qualquer "sim" é blocker. |

## Como registrar

Uma linha por pergunta, com a resposta literal e a data, em
`docs/canon/reports/SPEC-EXTRA-001.6-EXECUTION-REPORT.md` §6.4 ("validado pela atendente").
⛔ Não declarar aceite antes de recebê-lo.
