# SPEC-090 · O ATENDIMENTO DE ONTEM VIRA CONSERTO DE HOJE

> **O que ela entrega:** toda manhã dá para perguntar *"o que aconteceu ontem,
> o que falhou, e o que eu conserto hoje?"* — **e ter resposta com número.**
> Inclusive o que a Regina e a Saionara anotaram.
>
> **v1** · 26/08/2026 · commit base `ec8bc42` · repo `AutoBrokers-FIX`

---

## 🔴 A razão desta SPEC existir

O Founder descreveu o que vai fazer, e é isto:

> *"Enquanto os agentes vão atendendo e os humanos acompanhando no WhatsApp, a
> Central e um chat do Claude Code vão analisar todos os atendimentos e ver o
> que aconteceu, onde precisamos melhorar. E eu todos os dias vou colocar o
> Claude Code para analisar e ajustar os erros **e as anotações das atendentes
> humanas**."*

📊 **Duas coisas impedem isso hoje, e as duas foram medidas em 26/08:**

```
1  as três fontes não se juntam       não dá para dizer o que aconteceu
2  a anotação delas não tem porta      elas vão escrever FORA do produto
```

## 1.1 · 🔴 Três ilhas que não se falam

```
attendance_transcripts .... 156.443 linhas · 152.300 com session_id
   que casam com conversations.id ................. 0
   que casam com observed_sessions.id ............. 0
work_runs ................. nenhuma coluna de conversa ou sessão
                            só `thread_id = 'work:<uuid>'`
conversation_scorecards ... 686 de 686 casam com conversations ✅
```

> **"O cliente escreveu X, o robô abriu o chamado, travou na tela Y" é hoje
> impossível de reconstruir.**

⚠️ **E a proposta original não vê isso.** Ela lista *"conversation/thread; dispatch
session; Work Run; case"* como chaves **intercambiáveis**, como se juntar fosse um
`GROUP BY`. Não é: exige uma camada de resolução de identidade que a proposta
**não orça, não cita e não testa.**

## 1.2 · ✅ Mas metade do trabalho já está feita — e isso encurta a SPEC

📊 A SPEC-093 **já gravou o gravador**, e ele está na `main`:

```sql
SELECT payload_redacted->>'rota',  payload_redacted->>'tela',
       payload_redacted->>'motivo', payload_redacted->>'por', count(*)
  FROM work_events
 WHERE event_type IN ('travamento.aberto','travamento.destravado')
   AND created_at > now() - interval '7 days'
 GROUP BY 1,2,3,4;
```

📊 **Executada hoje: `[]`.** ⚠️ **Não falta código — falta o piloto rodar.** Na
segunda-feira ela enche sozinha, com `humano | cerebro | sentinela | vigia | robo`
na coluna de quem destravou.

> 🔴 **Isto muda o tamanho da SPEC:** o que a proposta orçava em 15 blocos e
> 3–4 semanas vira **4 blocos**, porque a esteira principal já existe.

## 1.3 · O que a proposta declarava e 📊 está vazio

| a proposta chama de "fundação existente" | medido em 26/08 |
|---|---|
| `company_memories` | **0 linhas** |
| `knowledge_candidates` | **0 linhas** |
| `capability_gaps` | **0 linhas** |
| `demand_clusters` | **0 linhas** |

⚠️ **E as duas fundações de verdade não aparecem na lista dela:**
`attendance_transcripts` (156k) e `knowledge_cards` (18.715). 🔴 Este último está
**parado desde 16/08 — dez dias.**

---

## 0. O TESTE DO PRODUTO

> **Terça de manhã. O Founder abre o chat e escreve: "o que aconteceu ontem?" —
> e recebe: quantos atendimentos, quantos travaram, em que telas, quem
> destravou, quanto tempo, e o que a Regina anotou.**

⛔ **Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado. NENHUM agente é ligado.
⛔ NENHUMA entrada em portal de seguradora.
⛔ Banco: SELECT livre; escrita só pelas migrations desta SPEC.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NÃO mexer em variável de ambiente de produção.
⛔ NUNCA `git add -A` (P-247).
```

---

# BLOCO A · 🔴 A chave de junção — sem ela nada mais funciona

## O problema

📊 152.300 transcripts com `session_id` que **não casam com nada**. E `work_runs`
sem coluna de conversa.

## O conserto — e ele é menor do que parece

⛔ **Não é uma tabela de identidade.** É uma coluna e um backfill.

```
work_runs  +  conversation_id  (nulo permitido, FK, índice)
             escrito por quem CRIA o run — o dispatch já tem a conversa na mão
```

E para o histórico: **um backfill que só liga o que dá para provar.**

⚠️ 🔴 **A regra que torna o backfill honesto:** ele liga por evidência
(telefone + janela de tempo + tenant), e **o que não casar com certeza fica
NULO.** ⛔ Um `conversation_id` errado é pior que nenhum: ele produz relatório
confiante e falso.

## O gate

```
① acionamento novo → `conversation_id` preenchido no ato
② backfill: o que ligou, ligou certo — amostra conferida à mão
③ 🔴 o que não deu para provar ficou NULO, e o número de NULOs é REPORTADO
   ⚠️ "backfill 100%" é a resposta suspeita, não a boa
④ dois tenants: nenhum run de A aponta para conversa de B
```

🔴 **A mutação:** afrouxe a regra de evidência (só telefone, sem janela) e o
teste ② tem de ficar **vermelho**.

---

# BLOCO B · A trajetória do travamento

## O problema

📊 Os eventos existem (`travamento.aberto`, `travamento.destravado`) e estão
vazios só porque o piloto não rodou. **Falta o que os transforma em história.**

## O conserto

Uma leitura, não um motor.

```
por travamento:  rota · tela · motivo · quem destravou · quanto tempo ficou
por dia:         quantos · quantos ficaram sem destravar
por rota:        as que mais travam — 🔴 é a lista de conserto do dia seguinte
```

⛔ **Nada de inferir "o atendimento foi bom".** 📊 `conversation_scorecards` já dá
nota, é 100% heurística e a média é **95,5** — 💭 uma régua que dá 95 para tudo
não separa dia bom de dia ruim, e a SPEC-089 é quem cuida disso.

## O gate

```
① travamento gravado → aparece na trajetória com os cinco campos
② destravado por humano → a trajetória diz `humano`, não `robo`
③ 🔴 travamento que NUNCA foi destravado aparece como tal   (é o mais importante)
④ dois tenants
```

---

# BLOCO C · 🔴 A anotação da Regina e da Saionara entra no produto

> **É o bloco que ninguém tinha visto, e ele decide se o piloto vira conserto ou
> vira conversa de WhatsApp perdida.**

## O problema

📊 **Não existe porta.** As duas vão assistir, ver o robô errar, e anotar — num
caderno, num grupo, num bloco de notas. **E aí o Claude Code não lê.**

## O conserto — o mais barato que resolve

⚠️ **Não é uma tela nova.** Elas já estão no WhatsApp o dia inteiro.

```
elas respondem a PRÓPRIA conversa com um prefixo combinado:
     #nota o robô perguntou a placa duas vezes

o Espelho já captura tudo que sai do telefone delas          ✅ existe
o produto reconhece o prefixo e grava como OBSERVAÇÃO HUMANA
     ligada à conversa, à rota e ao travamento mais recente
```

🔴 **E a nota NÃO vai para o segurado.** ⛔ O prefixo é consumido: a mensagem é
capturada, gravada e **não reenviada**.

⚠️ **Se o prefixo escapar uma vez, o cliente lê `#nota o robô errou`.** Por isso
o gate ② é o mais duro da SPEC.

## O gate

```
① ela escreve `#nota ...` → vira observação ligada à conversa
② 🔴 ZERO chance de o `#nota` chegar ao segurado
   ⚠️ e o teste conta `platform_sends` — não confia em leitura de código
③ mensagem normal dela (sem prefixo) → continua sendo mensagem, intocada
④ o Claude Code consegue ler todas as notas de um dia numa query
⑤ dois tenants
```

🔴 **A mutação obrigatória:** desligue o consumo do prefixo e ② tem de ficar
**vermelho**. Se continuar verde, o guarda não guarda nada — e o preço é o
cliente lendo o bastidor.

---

# BLOCO D · A pergunta de terça-feira

## O conserto

Uma consulta que responde tudo de uma vez, e uma tela que já existe mostrando o
resumo.

```
ontem:  N atendimentos · N travaram · as 3 telas que mais travaram
        quem destravou (humano/cérebro/sentinela/vigia)
        tempo mediano de travamento
        as notas da Regina e da Saionara
```

⚠️ **Sem tela nova.** 📊 `app/dashboard/atendimentos/fila` já existe.

## O gate

```
① a consulta responde com número, e o número bate com o banco
② dia sem atendimento → zeros, não erro
③ 🔴 o total nunca é maior que o que existe   (o `limit` silencioso mata relatório)
④ dois tenants
```

---

# BLOCO E · A prova

```
① os gates de A, B, C, D passam
② 🔴 os quatro agentes `attendance` continuam `is_active=false`
③ 🔴 ZERO mensagens enviadas durante toda a execução
④ a bateria inteira, com o número de rodadas do diário
⑤ dois tenants em todos os blocos
```

---

## 3. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

📊 A proposta tinha **15 blocos**. Doze saíram, e a razão é sempre a mesma:
**eles processam volume que ainda não existe.**

| peça | 📊 medido | **volta quando** |
|---|---|---|
| event envelope · actor/subject · permission | — | houver fonte externa conectada (é outra SPEC) |
| Episode | 🔴 depende do BLOCO A | depois do backfill |
| scope resolver · dedupe · router | `knowledge_candidates` = **0** | houver candidato |
| garimpo · backfill · incremental | — | houver volume |
| consolidar 5 motores numa *Demand Intelligence* | 📊 **3 dos 5 têm 0 linhas** | ⛔ consolidar vazio é criar peça nova com nome de consolidação |

> ⚠️ **Nada foi julgado ruim. Foi julgado cedo** — e cada linha tem gatilho
> medível.

---

## 4. O que fica pendente

```
P-090-01  🔴 12 de 16 tabelas medidas têm RLS ligada e ZERO policies —
          inclusive `attendance_transcripts`, `observed_events` e a
          `saudacoes_enviadas` criada ontem. `CLAUDE.md` §7.
P-090-02  `knowledge_cards` parado desde 16/08 (10 dias). 18.715 linhas e
          nenhuma nova. Ninguém percebeu.
P-090-03  `conversation_auditor.py` tem `limit(200)` + trava de 1×/dia:
          teto silencioso. Contra a §51 da própria proposta ("no silent zero").
P-090-04  4.143 transcripts sem `session_id`.
P-090-05  `conversation_scorecards` pula `dispatch:` de propósito
          (`conversation_auditor.py:159`) — acionamento não tem nota nenhuma.
```

---

## 5. A ordem de execução

```
A  →  B  →  C  →  D  →  E
```

💭 **~4h.** O BLOCO A domina (backfill com regra de evidência e amostra à mão).

🔴 **A vem primeiro e não é negociável:** B, C e D todos penduram na conversa, e
sem a chave de junção eles produzem relatório confiante sobre metade da história.
