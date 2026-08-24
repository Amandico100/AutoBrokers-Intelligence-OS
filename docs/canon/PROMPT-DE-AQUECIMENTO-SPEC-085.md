# PROMPT DE AQUECIMENTO — antes da SPEC-085

> **Cole isto inteiro num chat NOVO.** Não é a execução. É o que vem antes dela.
> 24/08/2026 · repo `AutoBrokers-FIX` · commit base `d8c37eb`

---

Você vai executar uma SPEC do **AutoBrokers.ai** — mas **ainda não.**

Antes disso, você vai **auditar o terreno com as próprias mãos** e responder um questionário. O objetivo não é você aprender o sistema: é você **calibrar o quanto desconfiar dele**.

## ⛔ AS TRAVAS. Valem a partir desta linha, inclusive nesta auditoria.

```
⛔ SOMENTE LEITURA. Nenhum arquivo alterado, nenhum commit, nenhum branch.
   No banco: SOMENTE SELECT. Nenhum INSERT/UPDATE/DELETE/ALTER/CREATE.

⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão desligados e
   continuam. A única forma de ligar é a corretora clicando no botão.

⛔ NENHUMA MENSAGEM SAI. Para ninguém, por nenhum canal, em hipótese alguma.

⛔ NUNCA imprima CPF, telefone, apólice, placa ou nome de pessoa. Mascare ou
   agregue. Se um número identifica alguém, ele não entra na sua resposta.

⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA. Nem uma. Bloqueio de conta é
   dano que não se desfaz.
```

## O QUE É O PRODUTO, em dez linhas

O AutoBrokers.ai é um SaaS multi-tenant para **corretoras de seguros**. O produto é um **atendente de IA que conversa com segurados no WhatsApp** e, quando o cliente precisa de assistência 24h — guincho, chaveiro, encanador, vidros, eletrodoméstico —, **ele mesmo conversa com a URA da seguradora** (Porto, Allianz, HDI, Yelum, Azul, Mapfre, Tokio, Zurich) para abrir o chamado.

Quando o carro de alguém está parado na estrada às onze da noite, **é este sistema que abre o chamado**. Quando ele erra, um segurado real fica sem socorro, ou a seguradora abre a ordem de serviço errada.

**Um "corredor" é o roteiro de uma rota** — `seguradora × ramo × serviço`. São **73**.

## ONDE ESTÁ TUDO

```
CLAUDE.md                                as regras invioláveis. Vence tudo.
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md  como se monta equipe, quem julga,
                                         quando o laço para
docs/canon/PENDENCIAS.md                 ~8.400 linhas do que ficou pendente
docs/canon/reports/                      os relatórios de execução
backend/app/services/                    o motor
backend/app/services/corridor_playbooks.py   os 73 corredores
```

Banco: MCP do Supabase, `project_id = dcajcvlzcjbmyapmklil`. Carregue com
`ToolSearch`, query `select:mcp__claude_ai_Supabase__execute_sql`.

---

# 🔴 A SUA TAREFA: MEDIR, NUNCA LER E ACREDITAR

**Este projeto tem uma regra que vale mais que todas as outras:**

> **📊 = MEDIDO** — sai com a data, a fonte, e a consulta ou o comando que o produziu.
> **💭 = ILUSTRATIVO** — hipótese ou exemplo, **nunca citável como fato**.
>
> 🔴 **Número sem marca, em documento novo, é defeito de revisão.**

E a razão de essa regra existir é a coisa mais importante deste prompt:

> **Hoje mesmo, quem tem o contexto inteiro deste projeto escreveu três afirmações erradas numa SPEC** — e cada uma passou por pelo menos um juiz antes de cair. **Duas delas teriam quebrado produção.**
>
> 🔴 **Se eu, que conheço o sistema, erro assim, você vai errar mais.** A defesa não é ler com atenção. **A defesa é medir.**

## As perguntas

Responda **as quinze**. Várias têm resposta óbvia **e errada** — de propósito. **Meça antes de responder.**

⚠️ **"Não sei" e "não consegui medir" são respostas valiosas.** O que não vale é responder de leitura o que só a medição decide.

---

**1.** Quantas conversas com **segurado no WhatsApp** o **robô** já teve, na história do produto? 📊 Traga a consulta. ⚠️ *A tabela `conversations` vai te dar um número. Pergunte-se se todas as linhas dela são do robô.*

**2.** Existe no backend um **mascarador de PII** aplicado aos dados da sessão de acionamento? Se sim, onde. Se não, **diga que não existe** e mostre o que você olhou.

**3.** 📊 **O `pytest` executa todos os testes de `backend/tests/`, e a suíte está verde.**
Confirme ou refute, com o número. ⚠️ *Se você refutar, diga também desde quando e o que mudou.*

**4.** O que acontece **hoje** quando o robô não consegue continuar com a seguradora? Descreva o caminho, com `arquivo:linha`. 🔴 **Quantos caminhos diferentes existem?**

**5.** Um atendimento que travou **há dez horas** — onde ele está registrado? Consegue ser visto? Por quem?

**6.** 📊 Quantas corretoras existem, e **quantas têm destino de suporte humano configurado**? O que acontece com as que não têm?

**7.** `INSURER_DISPATCH_LIVE` — o que é, qual o padrão hoje, e **quem pode mudá-lo**? 🔴 E o que mais precisa estar verdadeiro para uma mensagem chegar de fato a uma seguradora?

**8.** 📊 **O Atlas é o mapa das telas das URAs, desenhado à mão a partir das SPECs e dos
manuais das seguradoras.** Confirme ou refute. Quantos nós tem, e de onde eles vieram?

**9.** 📊 Qual foi o **único** atendimento ponta a ponta, com cliente real e sem travas, que este produto já fez? Quando? 🔴 **Por que ele importa mais que todos os outros dados do banco?**

**10.** Abra `docs/canon/PENDENCIAS.md` e ache **três pendências abertas que afirmam um fato que já não é verdade**. 📊 Prove que mudaram. ⚠️ *Elas existem. Uma foi fechada hoje exatamente por isso.*

**11.** Pelo `PROTOCOLO-AUTOBROKERS-AAA.md` §2: **quantos agentes** merece a tarefa *"trocar uma palavra numa mensagem que o segurado lê"*? Mostre as duas contas com os quatro números. 🔴 E a tarefa *"corrigir uma palavra num `COMMENT ON COLUMN` do banco"*?

**12.** O protocolo tem uma regra que decide **se um achado é blocker ou pendência**. Qual é, e **por que ela existe**? 🔴 Dê um exemplo de achado que **parece grave e não é**.

**13.** 📊 O `.github/workflows/gate.yml` roda o quê? 🔴 E o que ele **não** roda que deveria?

**14.** 🔴 **Ache um defeito real neste repositório que ninguém te apontou.** Um só, com evidência. ⚠️ *Não invente. Se procurar de verdade e não achar, diga onde procurou — isso também é resposta.*

**15.** 🔴 **Liste o que você NÃO entendeu.**
⛔ *"Entendi tudo" é resposta reprovada.* Este sistema tem 73 corredores, quatro vigias que não se conhecem, três cadeias de handoff e ~8.400 linhas de pendências. **Ninguém entende tudo em uma tarde.** O que eu preciso saber é **onde está o seu ponto cego**, porque é lá que a execução vai doer.

---

## COMO RESPONDER

- **Evidência em cada resposta.** `arquivo:linha`, a consulta SQL, ou a saída do comando. Sem isso, a resposta não conta.
- Separe **FATO** (medi) de **INFERÊNCIA** (deduzi).
- **Seja breve onde a resposta é simples** e denso onde ela não é. Não encha linguiça: eu vou ler tudo.
- 🔴 **DUAS DAS QUINZE AFIRMAM ALGO FALSO, com todas as letras.** Ache-as e refute com o
  número. ⚠️ Elas estão assinadas por quem está te dando a tarefa — **é exatamente esse o
  teste.** Na execução, a SPEC vai te afirmar coisas erradas do mesmo jeito, e você é a
  última linha de defesa antes do segurado.

## E o que acontece depois

Você me manda as quinze respostas. **Eu corrijo o que estiver torto, aponto o que você não viu, e só então você recebe a SPEC.**

⚠️ **Isto não é uma prova.** É o que separa um executor que descobre o sistema **durante** o trabalho — errando caro — de um que chega sabendo onde o chão é falso.

> 🔴 **E a coisa mais importante que você pode levar deste aquecimento:**
> **quando a SPEC disser algo que você mediu diferente, a SPEC está errada até prova em contrário.** Meça, mostre o número, e devolva.
> **Foi assim que os quatro piores defeitos do documento foram encontrados.**
