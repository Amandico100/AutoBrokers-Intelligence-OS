# AQUECIMENTO — antes da SPEC-093

> **Cole isto inteiro num chat NOVO, aberto em `AutoBrokers-FIX`.**
> Não é a execução: é o que vem antes. 💭 ~20 minutos.
> 25/08/2026 · commit base `b8ef4e5`

---

Você vai executar uma SPEC do **AutoBrokers.ai** — mas **ainda não.**

Primeiro você audita o terreno com as próprias mãos e responde doze perguntas.
**O objetivo não é aprender o sistema. É calibrar o quanto desconfiar dele.**

## ⛔ AS TRAVAS. Valem a partir desta linha.

```
⛔ SOMENTE LEITURA no aquecimento. Nada alterado, nada commitado. No banco: só SELECT.
⛔ NENHUMA MENSAGEM SAI. Para ninguém, por nenhum canal.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA. Bloqueio de conta não se desfaz.
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão desligados e continuam.
⛔ NÃO tocar em variável de ambiente de produção.
⛔ NUNCA imprima CPF, telefone, apólice, placa ou nome de pessoa.
```

## O PRODUTO, em oito linhas

O AutoBrokers.ai é um SaaS multi-tenant para **corretoras de seguros**. O produto
é um **atendente de IA que conversa com segurados no WhatsApp** e, quando alguém
precisa de assistência 24h — guincho, chaveiro, pneu —, **ele mesmo conversa com
a URA da seguradora, pelo WhatsApp**, para abrir o chamado. O caminho por cada
URA chama-se **corredor**.

🔴 **A corretora vai ligar o atendimento para clientes REAIS em dias.** Duas
atendentes humanas (Regina e Saionara) vão **assistir pelo WhatsApp delas** e,
quando o robô travar, **dar um clique para ele seguir**. ⛔ **Elas não assumem o
atendimento.** A SPEC-093 é o que falta para isso funcionar.

## A LEITURA — 🔴 o NÚCLEO, e nada além

```
CLAUDE.md
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md       🔴 inteiro. É curto de propósito.
docs/canon/GLOSSARIO.md
docs/canon/specs/SPEC-093-o-atendimento-real-liga-e-funciona.md
```

⛔ **NÃO leia o `PENDENCIAS.md`** (437 KB, e a §1 do protocolo proíbe). As que
interessam, **por número**: `P-168` · `P-231` · `P-246` · `P-247` · `P-248`.

Banco: MCP do Supabase, `project_id = dcajcvlzcjbmyapmklil`
(`ToolSearch`, query `select:mcp__claude_ai_Supabase__execute_sql`).

---

# 🔴 A REGRA QUE VALE MAIS QUE TODAS

> **📊 = MEDIDO** — com a data, a fonte, e a consulta que produziu o número.
> **💭 = ILUSTRATIVO** — hipótese. **Nunca citável como fato.**

E a razão é a coisa mais importante deste prompt:

> **A SPEC que você vai receber foi escrita depois de três lentes independentes
> revisarem a proposta anterior. Elas acharam, entre outras coisas, que a
> proposta afirmava ter fundações que 📊 têm 0, 1 e 4 linhas no banco.**
>
> 🔴 **Quem conhece o sistema inteiro erra assim. Você vai errar mais. A defesa
> não é ler com atenção: é medir.**

## As doze perguntas

⚠️ **Várias têm resposta óbvia E ERRADA, de propósito.** E **"não sei" é resposta
valiosa** — o que não vale é responder de leitura o que só a medição decide.

---

**1.** 📊 Quantas conversas de WhatsApp o **robô** já teve com um segurado, na
história deste produto? ⚠️ *Cuidado: a maior parte de `messages` é espelho de
conversa **humana**. Separe.*

**2.** 📊 `company_members`: quais papéis existem, e quantas pessoas em cada um?
🔴 E qual papel a Regina e a Saionara precisam ter para apertar o botão de ligar
o agente hoje?

**3.** 🔴 **A allowlist de entrada.** Ache-a no código. O que acontece com um
telefone que não está nela — a mensagem é guardada, descartada, ou bufferizada?
`arquivo:linha`.

**4.** 📊 Com o agente **desligado**, o que acontece com a mensagem de um cliente?
E **ao religar**, o que acontece com as que chegaram no intervalo? *Siga o
caminho, não presuma.*

**5.** 🔴 **O clique da atendente.** Quando uma pessoa responde pelo WhatsApp da
corretora e o corredor segue, **o produto registra que foi um humano?** Prove
pelo dado, não pelo código.

**6.** Para **Vigia**, **Sentinela** e **Cérebro**: onde cada um mora, quando
dispara, e 📊 **quantas vezes cada um já destravou um acionamento?**
⚠️ *Um dos três não deixa rastro nenhum em banco. Descubra qual.*

**7.** 📊 **`work_effects` é a autoridade de efeitos externos deste produto, e a
SPEC-093 vai usá-la para idempotência.** Confirme ou refute, com o número.

**8.** 🔴 `INSURER_DISPATCH_LIVE`, `DISPATCH_FINALIZE_MODE`,
`ACIONAMENTO_FREIO_DE_EMERGENCIA`. Para cada uma: **o padrão no código** e **o
valor real em produção**. ⚠️ *Existe um jeito de ler os três sem abrir o
EasyPanel. Ache-o.*

**9.** 📊 **Ligar um corredor na tela de Corredores liga o canal e passa a
enviar mensagem para a seguradora.** Confirme ou refute, com `arquivo:linha`.

**10.** 🔴 **Esvaziar a `ATTENDANT_INBOUND_ALLOWLIST` quebra alguma outra coisa
do produto?** Procure quem mais a lê. ⚠️ *Esta é a pergunta que mais separa quem
mediu de quem leu.*

**11.** 🔴 **Ache um defeito real neste assunto que a SPEC-093 não aponta.** Um
só, com evidência. ⚠️ *Não invente. "Procurei em X, Y e Z e não achei" também é
resposta.*

**12.** 🔴 **Liste o que você NÃO entendeu.**
⛔ *"Entendi tudo" é resposta reprovada.* Este assunto tem duas tabelas de acervo
que não se falam, 73 corredores, três destravadores e um clique que não deixa
rastro. **Ninguém entende tudo numa tarde.** Eu preciso saber **onde está o seu
ponto cego**, porque é lá que a execução vai doer.

---

## COMO RESPONDER

- **Evidência em cada resposta**: `arquivo:linha`, a consulta SQL, ou a saída do
  comando.
- **FATO** (medi) separado de **INFERÊNCIA** (deduzi).
- Breve onde a resposta é simples, denso onde não é. **Eu vou ler tudo.**
- 🔴 **DUAS DAS DOZE AFIRMAM ALGO FALSO, com todas as letras.** Ache-as e refute
  **com o número**. ⚠️ Elas estão assinadas por quem está te dando a tarefa — **é
  exatamente esse o teste.** Na execução, a SPEC vai te afirmar coisas erradas do
  mesmo jeito, **e você é a última linha de defesa antes do segurado.**

## Depois

Você manda as doze respostas. **Eu corrijo o que estiver torto, aponto o que você
não viu, e aí você executa a SPEC-093 do começo ao fim, sem parar.**

> 🔴 **E o que você mais leva daqui:**
> **quando a SPEC disser algo que você mediu diferente, a SPEC está errada até
> prova em contrário.** Meça, mostre o número, e devolva.
> **Foi assim que os piores defeitos das três últimas SPECs foram encontrados — e
> um deles pela pessoa que estava no seu lugar.**
