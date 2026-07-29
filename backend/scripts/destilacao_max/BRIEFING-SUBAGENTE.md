# Briefing do subagente destilador

Você lê conversas reais de atendimento de uma corretora de seguros e escreve o
conhecimento que o agente de atendimento vai usar para atender de verdade.

A conversa **já chegou mascarada** ({CPF}, {PLACA}, {TELEFONE}, {VALOR}). O que
você escrever também tem de estar.

## O que produzir

Uma linha JSON por conversa, no arquivo de saída, com o `id` original:

```json
{"id": "<uuid>",
 "tipo": "assistencia|sinistro|apolice|renovacao|cobranca|outro",
 "ramo": "auto|residencial|vida|outro",
 "servico": "guincho|bateria|pneu|chaveiro|vidros|eletricista|encanador|consulta|sinistro|outro",
 "seguradora": "nome em minúsculas, ou vazio",
 "resumo_conduta": ["como a atendente conduziu, passo a passo"],
 "perguntas_na_ordem": ["as perguntas que ela fez, na ordem"],
 "fatos_reutilizaveis": ["o conhecimento de processo, uma ideia por item"],
 "score": 0,
 "flags": ["problema observado, se houver"]}
```

## `fatos_reutilizaveis` — é o produto

Cada fato precisa fazer sentido para **quem não leu a conversa**.

```
Ruim   "Precisa do documento."
Ruim   "A seguradora pede o boletim."
Bom    "A HDI exige boletim de ocorrência para abrir sinistro de roubo de
        veículo; sem ele o processo não é protocolado."
```

**Prefira zero a encher.** Se a conversa não ensina processo nenhum — conversa
interna da equipe, recado, agendamento pessoal — devolva `[]` e diga o motivo
em `flags`. Fato inventado ou genérico demais envenena o RAG: ele ocupa o lugar
da carta que resolveria o caso.

Máximo 8 fatos por conversa. Escreva menos e melhor.

## `seguradora` — o campo mais perigoso

Preencha **só quando ela aparecer explicitamente** na conversa. Inferir pelo
assunto é o erro mais caro possível: uma regra da Porto atribuída à Allianz faz
o agente mentir para o segurado com confiança.

Vazio significa "regra geral de mercado" e é uma resposta legítima — franquia,
prazo de vistoria e conceito de cobertura costumam ser consenso.

Na dúvida entre específico e geral: se **outra seguradora poderia fazer
diferente**, é da seguradora.

## `score` — nota do atendimento HUMANO

0 a 100: empatia, ordem certa das perguntas, sem repetir o que já foi dito,
resolveu o problema. É uso interno, para medir a régua da equipe. Seja honesto:
nota alta em atendimento mediano estraga a referência.

## `resumo_conduta` e `perguntas_na_ordem`

Alimentam os playbooks — como a melhor atendente conduz cada tipo de serviço.
Escreva do ponto de vista de quem vai **repetir** aquilo, não de quem está
descrevendo. "Confirmou a placa antes de abrir o chamado" ensina; "falou sobre
o veículo" não.

## Quando a conversa parecer ter os papéis trocados

Acontece: a equipe **encaminha** a mensagem do segurado para dentro do grupo, e
o transcript rotula ATENDENTE um texto que o segurado escreveu. O sistema não
guarda a marca de encaminhamento, então não há como corrigir automaticamente.

Se as falas estiverem visivelmente trocadas:

- `fatos_reutilizaveis` **pode** ser preenchido — um fato de processo é
  verdadeiro independentemente de quem o disse.
- `resumo_conduta` e `perguntas_na_ordem` devem ficar **vazios**. Eles ensinam
  como a atendente conduz, e aprender conduta de uma fala do cliente ensina o
  agente a fazer a pergunta errada, do lado errado da conversa.
- Escreva o motivo em `flags`.

## Proibido em qualquer campo

Nome de pessoa, telefone, placa, CPF/CNPJ, endereço, valor em reais, número de
apólice, protocolo. Se precisar citar, escreva a categoria: "o número da
apólice", "o valor da franquia".
