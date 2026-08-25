# AQUECIMENTO — antes da SPEC-092

> **Cole isto inteiro num chat NOVO.** Não é a execução: é o que vem antes.
> 25/08/2026 · repo `AutoBrokers-FIX`

---

Você vai executar uma SPEC do **AutoBrokers.ai** — mas **ainda não.**

Primeiro você audita o terreno com as próprias mãos e responde treze perguntas. **O objetivo não é aprender o sistema. É calibrar o quanto desconfiar dele.**

## ⛔ AS TRAVAS. Valem a partir desta linha.

```
⛔ SOMENTE LEITURA. Nada alterado, nada commitado. No banco: só SELECT.
⛔ NENHUMA MENSAGEM SAI. Para ninguém, por nenhum canal.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA. Bloqueio de conta não se desfaz.
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão desligados.
⛔ NUNCA imprima CPF, telefone, apólice, placa ou nome de pessoa.
```

## O PRODUTO, em oito linhas

O AutoBrokers.ai é um SaaS multi-tenant para **corretoras de seguros**. O produto é um **atendente de IA que conversa com segurados no WhatsApp** e, quando alguém precisa de assistência 24h — guincho, chaveiro, pneu —, **ele mesmo conversa com a URA da seguradora, pelo WhatsApp**, para abrir o chamado.

🔴 **Quatro seguradoras — Yelum, HDI, Porto e Azul — pararam de perguntar por texto e passaram a abrir um FORMULÁRIO NATIVO dentro da conversa** (um mini-app: listas, botões, campos). Quando isso acontece, **o corredor para**. 📊 São **460 apólices de auto — 26,9% da carteira.**

## A LEITURA — 🔴 o NÚCLEO, e nada além

```
CLAUDE.md
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md      🔴 leia inteiro. É curto de propósito.
docs/canon/GLOSSARIO.md
docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md  🔴 243 linhas. É a prova do envio.
```

⛔ **NÃO leia o `PENDENCIAS.md`.** São 421 KB, e a §1 do protocolo proíbe. As que interessam, **por número**: `P-084-38` · `P-084-67` · `P-084-68` · `P-084-69`.

Banco: MCP do Supabase, `project_id = dcajcvlzcjbmyapmklil` (`ToolSearch`, query `select:mcp__claude_ai_Supabase__execute_sql`).

---

# 🔴 A REGRA QUE VALE MAIS QUE TODAS

> **📊 = MEDIDO** — com a data, a fonte, e a consulta que produziu o número.
> **💭 = ILUSTRATIVO** — hipótese. **Nunca citável como fato.**

E a razão é a coisa mais importante deste prompt:

> **Na SPEC anterior, quem tem o contexto inteiro deste projeto escreveu três afirmações erradas — e duas teriam quebrado produção.** O executor achou **cinco erros do autor** antes de escrever uma linha de código.
>
> 🔴 **Se quem conhece o sistema erra assim, você vai errar mais. A defesa não é ler com atenção: é medir.**

## As treze perguntas

⚠️ **Várias têm resposta óbvia E ERRADA, de propósito.** E **"não sei" é resposta valiosa** — o que não vale é responder de leitura o que só a medição decide.

---

**1.** 📊 Quantas vezes um **formulário nativo** já foi respondido no acervo deste produto? Por seguradora. ⚠️ *Cuidado: existe mais de uma tabela de acervo.*

**2.** 🔴 **Quem** respondeu esses formulários — o robô ou uma pessoa? 📊 Prove pelo dado.

**3.** 📊 **O convite** do formulário — a mensagem que a seguradora manda **para nós** — está no acervo? Quantas vezes? ⚠️ *Esta pergunta e a nº 1 têm respostas muito diferentes, e a diferença é o assunto da SPEC.*

**4.** 📊 **O corredor já reconhece o formulário nativo: o marcador `[FORMULARIO NATIVO]` aparece no acervo.** Confirme ou refute, com o número.

**5.** Abra `evolution_inbound.py`. Que rótulos de mensagem interativa o parser reconhece? 🔴 E qual rótulo aparece nas respostas reais que você achou na pergunta 1?

**6.** 📊 **O caminho de ENVIO está provado e correto — não há nada a consertar nele.** Confirme ou refute. ⚠️ *Se refutar, mostre o campo e a captura.*

**7.** Quantas rotas (`seguradora × ramo × serviço`) travam por causa do formulário? **Nomeie-as**, com a evidência.

**8.** 🔴 **Porto e Azul.** O que o produto sabe sobre o formulário delas? O que dá para fazer, e o que **não** dá?

**9.** O que acontece **hoje** com o segurado quando o formulário aparece e o corredor não consegue responder? Descreva o caminho, com `arquivo:linha`.

**10.** 🔴 **Existe jeito de testar o envio de um formulário SEM mandar mensagem para uma seguradora?** Se sim, qual — e **que risco ele tem hoje**?

**11.** `INSURER_DISPATCH_LIVE`, `CARTOGRAPHER_MODE`, `ACIONAMENTO_FREIO_DE_EMERGENCIA`. Para cada uma: o padrão hoje, e 🔴 **qual delas PROTEGE e qual ATRAPALHA um teste de formulário.**

**12.** 🔴 **Ache um defeito real neste assunto que ninguém te apontou.** Um só, com evidência. ⚠️ *Não invente. "Procurei em X, Y e Z e não achei" também é resposta.*

**13.** 🔴 **Liste o que você NÃO entendeu.**
⛔ *"Entendi tudo" é resposta reprovada.* Este assunto tem duas tabelas de acervo que não se falam, quatro seguradoras, um convite que nunca foi capturado e um envio provado uma vez. **Ninguém entende tudo numa tarde.** Eu preciso saber **onde está o seu ponto cego**, porque é lá que a execução vai doer.

---

## COMO RESPONDER

- **Evidência em cada resposta**: `arquivo:linha`, a consulta SQL, ou a saída do comando.
- **FATO** (medi) separado de **INFERÊNCIA** (deduzi).
- Breve onde a resposta é simples, denso onde não é. **Eu vou ler tudo.**
- 🔴 **DUAS DAS TREZE AFIRMAM ALGO FALSO, com todas as letras.** Ache-as e refute **com o número**. ⚠️ Elas estão assinadas por quem está te dando a tarefa — **é exatamente esse o teste.** Na execução, a SPEC vai te afirmar coisas erradas do mesmo jeito, **e você é a última linha de defesa antes do segurado.**

## Depois

Você manda as treze respostas. **Eu corrijo o que estiver torto, aponto o que você não viu, e só então você recebe a SPEC.**

> 🔴 **E o que você mais leva daqui:**
> **quando a SPEC disser algo que você mediu diferente, a SPEC está errada até prova em contrário.** Meça, mostre o número, e devolva.
> **Foi assim que os piores defeitos das duas últimas SPECs foram encontrados — e um deles pela pessoa que estava no seu lugar.**
