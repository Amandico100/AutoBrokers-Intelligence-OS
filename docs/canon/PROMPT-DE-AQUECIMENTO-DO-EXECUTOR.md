# AQUECIMENTO DO EXECUTOR — cole num chat NOVO, antes de qualquer SPEC

> **Chat novo, aberto em `AutoBrokers-FIX`. Ele não conhece nada.**
> 💭 ~30 minutos. **Não pule.** 📊 O aquecimento tirou **96/100** no placar de
> mecanismos do protocolo — é o segundo mais valioso que este projeto mede.
>
> 30/08/2026

---

Você vai executar SPECs do **AutoBrokers.ai** — mas **ainda não.**

Primeiro você audita o terreno com as próprias mãos e responde treze perguntas.

> 🔴 **O objetivo não é aprender o sistema. É calibrar o quanto desconfiar dele.**

---

## ⛔ AS TRAVAS. Valem a partir desta linha, e não têm exceção.

```
⛔ SOMENTE LEITURA no aquecimento. No banco: só SELECT.
⛔ NENHUMA MENSAGEM SAI. Para segurado ou seguradora, por nenhum canal.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA. Bloqueio de conta não se desfaz.
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão `is_active=false`.
⛔ NÃO tocar em variável de ambiente de produção.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NUNCA `git add -A` — arquivo por arquivo.
```

⚠️ **A última não é preciosismo.** 📊 Um `git add -A` levou uma mutação de teste
para dentro de um commit, **duas vezes**, e o guarda que existia para impedir
isso olhava o `HEAD` — que ainda era o commit anterior.

---

## O PRODUTO, em oito linhas

O **AutoBrokers.ai** é um SaaS multi-tenant para **corretoras de seguros**. O
produto é um **atendente de IA que conversa com segurados no WhatsApp** e, quando
alguém precisa de assistência 24h — guincho, chaveiro, pneu —, **ele mesmo
conversa com a URA da seguradora, pelo WhatsApp**, para abrir o chamado.

O caminho por cada URA chama-se **corredor**. Cada
`seguradora × ramo × serviço` é uma **rota**. 📊 São **73**.

⚠️ **E o estado real, que quase ninguém adivinha:** 📊 o robô conversou com um
segurado **61 vezes na história inteira do produto**, e completou **3
acionamentos**. **A capacidade existe e quase não foi exercida.**

---

## 🔴 O PROTOCOLO É LEI — leia inteiro antes de responder

```
CLAUDE.md
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md      🔴 INTEIRO. É a v10.
docs/canon/GLOSSARIO.md
docs/canon/INDICE-DE-SPECS.md                 a fila e a ordem
```

⛔ **NÃO leia o `PENDENCIAS.md` inteiro** (437 KB). Só por número.

📊 **Por que o protocolo é lei, e não recomendação:** ele rodou em **2 de 6**
SPECs recentes. A causa não foi desobediência — os prompts das outras quatro
**não o carregavam**. E o custo:

```
COM o protocolo    47 achados · 22 defeitos de PRODUTO   →  23,5 por SPEC
SEM                19 achados ·  0 defeitos de produto   →   6,3 por SPEC
```

⚠️ **E a diferença é de CLASSE, não de volume.** Sem ele, os achados eram
*"guardas que não guardavam"*. Com ele: **vazamento entre corretoras**, resposta
em dobro ao segurado, `RecursionError` derrubando o webhook.

Banco: MCP do Supabase, `project_id = dcajcvlzcjbmyapmklil`
(`ToolSearch`, query `select:mcp__claude_ai_Supabase__execute_sql`).

---

# 🔴 A REGRA QUE VALE MAIS QUE TODAS

> **📊 = MEDIDO** — com a data, a fonte, e a consulta que produziu o número.
> **💭 = ILUSTRATIVO** — hipótese. **Nunca citável como fato.**

E a razão é a coisa mais importante deste documento:

> 📊 **Na última leva, o executor derrubou NOVE afirmações das SPECs que
> recebeu** — inclusive um orçamento de *"5 horas"* que ele mediu em **9m59**, e
> uma premissa central que ele refutou com **12.398 sessões** contra a amostra de
> 95 que a SPEC usara.
>
> 🔴 **Quem escreve estas SPECs erra assim. Você vai receber SPEC errada. A
> defesa não é ler com atenção: é medir.**

---

# AS TREZE PERGUNTAS

⚠️ **Várias têm resposta óbvia E ERRADA, de propósito.** E **"não sei" é resposta
valiosa** — o que não vale é responder de leitura o que só a medição decide.

---

**1.** 📊 Quantas conversas de WhatsApp o **robô** já teve com um segurado?
⚠️ *A maior parte de `messages` é espelho de conversa **humana**. Separe.*

**2.** 📊 Quantas rotas existem, quantas a régua consegue medir, e **quantas são
AAA hoje**? ⚠️ *Existem dois modos de rodar a régua, e eles dão números
diferentes. Diga qual você usou e por quê.*

**3.** 🔴 **O que acontece quando a seguradora manda uma tela que o corredor não
conhece?** Siga o caminho com `arquivo:linha`. E 📊 **quantas telas assim
chegaram nos últimos 45 dias?**

**4.** 📊 **Quantas conversas o produto já marcou como resolvidas?** ⚠️ *Esta
pergunta tem uma resposta que parece defeito de medição e não é.*

**5.** 🔴 **Quem destrava um acionamento travado?** Nomeie os três mecanismos,
diga onde cada um mora, e 📊 **quantas vezes cada um já agiu.**

**6.** 🔴 **Se uma atendente humana clicar no WhatsApp para destravar, o produto
registra que foi um humano?** Prove pelo dado, não pelo código.

**7.** 📊 **A bateria de testes está verde hoje.** Confirme ou refute — e se
houver vermelho, diga **se ele é defeito de produto ou infraestrutura conhecida**.

**8.** 🔴 `INSURER_DISPATCH_LIVE`, `DISPATCH_FINALIZE_MODE`,
`ACIONAMENTO_FREIO_DE_EMERGENCIA`. Para cada uma: **o padrão no código** e **o
valor real em produção**. ⚠️ *Existe um jeito de ler os três sem abrir o painel
do EasyPanel. Ache-o.*

**9.** 📊 **Toda tabela do produto tem RLS com policy, então o isolamento entre
corretoras está garantido pelo banco.** Confirme ou refute — e **explique o que
realmente protege.**

**10.** 🔴 **Quantas vezes a bateria de testes roda numa SPEC, e que fração do
relógio ela consome?** ⚠️ *Existe um arquivo que responde isso sozinho. Ache-o.*

**11.** 📊 **O protocolo AAA tem uma seção de REFERÊNCIA que nomeia artefatos que
você consegue abrir.** Confirme ou refute, **listando os que existem**.

**12.** 🔴 **Ache um defeito real no produto que ninguém te apontou.** Um só, com
evidência. ⚠️ *Não invente. "Procurei em X, Y e Z e não achei" também é resposta.*

**13.** 🔴 **Liste o que você NÃO entendeu.**
⛔ *"Entendi tudo" é resposta reprovada.* Este projeto tem **duas tabelas de
acervo que não se falam**, 73 rotas, três destravadores, quatro freios em série e
um corredor de 10.819 linhas. **Ninguém entende tudo numa tarde.** Eu preciso
saber **onde está o seu ponto cego**, porque é lá que a execução vai doer.

---

## COMO RESPONDER

- **Evidência em cada resposta**: `arquivo:linha`, a consulta SQL, ou a saída do
  comando.
- **FATO** (medi) separado de **INFERÊNCIA** (deduzi).
- Breve onde a resposta é simples, denso onde não é. **Eu vou ler tudo.**
- 🔴 **TRÊS DAS TREZE AFIRMAM ALGO FALSO, com todas as letras.** Ache-as e refute
  **com o número**. ⚠️ Elas estão assinadas por quem está te dando a tarefa — **é
  exatamente esse o teste.** Na execução, a SPEC vai te afirmar coisas erradas do
  mesmo jeito, **e você é a última linha de defesa antes do segurado.**

## Depois

Você manda as treze respostas. **Eu corrijo o que estiver torto, aponto o que
você não viu, e só então você recebe a primeira SPEC.**

> 🔴 **E o que você mais leva daqui:**
> **quando a SPEC disser algo que você mediu diferente, a SPEC está errada até
> prova em contrário.** Meça, mostre o número, e devolva.
>
> **Foi assim que os piores defeitos das últimas cinco SPECs foram encontrados —
> e nove deles pela pessoa que estava no seu lugar.**
