<!-- HISTÓRICO: anterior à v11 do protocolo (03/09/2026). Não é pacote vivo; os pacotes vivos estão em docs/canon/pacotes/. -->
# PROMPT DE EXECUÇÃO — a leva, uma SPEC de cada vez

> **Cole no MESMO chat que respondeu o aquecimento**, depois de eu corrigir as
> treze respostas. ⛔ **Nunca num chat frio.**
>
> 30/08/2026 · serve para qualquer leva — troque só a lista da §1

---

Você passou pelo aquecimento. **Agora executa.**

---

## 0 · 🔴 O PROTOCOLO É LEI — e ele é o PRIMEIRO item do pacote

**Antes de qualquer coisa, leia:**

```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md
   🔴 §0 · §0.2 · §0.3 · §1 · §2 · §3 · §5      é a v10, e é LEI
   ⚠️ a §1 (a DIETA) manda carregar ESTAS seções, não o documento inteiro
CLAUDE.md                                    §9.1 · §9.2 · §9.3 · §11 · §12.1
docs/canon/INDICE-DE-SPECS.md                a fila e a ordem
```

📊 **Por que ele é lei, e não recomendação:** ele rodou em **2 de 6** SPECs
recentes. A causa não foi desobediência — **os prompts das outras quatro não o
carregavam.** E o custo:

```
COM o protocolo    47 achados · 22 defeitos de PRODUTO   →  23,5 por SPEC
SEM                19 achados ·  0 defeitos de produto   →   6,3 por SPEC
```

⚠️ **E a diferença é de CLASSE, não de volume.** Sem ele, os achados eram
*"guardas que não guardavam"*. Com ele: **vazamento entre corretoras**, resposta
em dobro ao segurado, `RecursionError` derrubando o webhook.

> 🔴 **E este próprio prompt esteve sem ele até 02/09/2026.** 📊 4 de 10 pacotes
> de execução não carregavam o protocolo, e este era um dos quatro — **é o
> assunto da SPEC-091 que você vai executar.**

### 🔴 A §0.3 é nova, e nasceu destas duas SPECs

```
duas medições certas NÃO fazem uma causa certa

a afirmação é "A acontece PORQUE B"?
   medi A?  ✓    medi B?  ✓    🔴 medi que B CHEGA em A?  ← ninguém dá este passo
```

📊 **Três formas do mesmo erro, todas cometidas nestas SPECs:** código morto
(a linha existe e um `return` acima impede que rode) · meia regra (é `A E B` e
só `A` foi contado) · fonte de ontem (o número é certo, mas quem escreve mudou).

---

## 1 · A LEVA — nesta ordem, uma de cada vez

```
1º   docs/canon/specs/SPEC-088-*.md
2º   docs/canon/specs/SPEC-091-*.md
```

🔴 **A ordem vem do `INDICE-DE-SPECS.md`, e ela não é negociável.** Estas duas são
os únicos buracos na sequência `081 → 093`. **Depois delas a numeração fica
inteira.**

⛔ **Não pule para a seguinte antes de fechar a anterior** — relatório escrito,
bateria rodada, commit feito.

🔴 **E saiba o que você está recebendo:** 📊 estas duas SPECs passaram por
**três juízes independentes e três rodadas de conserto** em 02/09. Cada rodada
achou defeitos na anterior. **A última tirou os números medidos da prosa e os
trocou por comandos** — onde você ler *"conte você"*, é de propósito: aquele
contador já envelheceu três vezes.

> ⚠️ **O BLOCO 0 é o quarto juiz, e ele é seu.** Remeça tudo antes de codar.
> Se o seu número for diferente, **o SEU vence.**

⚠️ **E se uma delas vier com o veredito *"continua adiada"*:** isso é entrega
completa, não desistência. **Escreva o relatório dizendo por quê, com a medição
de hoje, e passe para a próxima.**

---

## 2 · ⛔ AS TRAVAS — valem em toda a leva

```
⛔ NENHUMA MENSAGEM SAI. Para segurado OU seguradora, por nenhum canal.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA.
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão `is_active=false`.
⛔ NÃO tocar em variável de ambiente de produção.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NUNCA `git add -A` — arquivo por arquivo.
⛔ Banco: SELECT livre; escrita só pelas migrations da SPEC.
```

## 3 · 🔴 PREFLIGHT — antes de cada SPEC, não só da primeira

```bash
git rev-parse --show-toplevel            # AutoBrokers-FIX
git rev-list --count HEAD..origin/main   # 🔴 TEM DE SER 0
git rev-list --count origin/main..HEAD   # ⚠️ o que ainda NÃO subiu
git status --short                       # limpo
```

⚠️ **A segunda linha existe porque já custou caro:** 43 commits ficaram no
computador do Founder enquanto ele clicava "Implantar" e recebia o código de dias
antes. **Estar em dia não é o mesmo que ter subido.**

---

## 4 · 🔴 O EXECUTION CARD — antes de escrever a primeira linha de código

**Cuspa isto e só depois comece.** É o `PROTOCOLO-AAA` §0.2, e é **obrigatório**:

```
OUTCOME ..............
RISCO ................  0–8    alcance + reversibilidade + frequência   (§3)
SUPERFÍCIE ...........  0–3                                             (§3)
PISO APLICADO ........  qual, e por quê                                 (§3.2)
UNIDADES .............
COESÃO ...............  o que fica JUNTO, e por quê                     (§3.4)
PARALELISMO REAL .....  quantos escritores ao mesmo tempo — ou "nenhum"
TIME .................  os papéis que a conta pediu                     (§4)
REFERÊNCIA ...........  o artefato que o juiz vai ABRIR                 (§7.1)
GATES ................
FAIXA DE RELÓGIO .....  ex.: 1–2h   ·  faixa, nunca promessa
```

📊 **Por que ele é obrigatório:** a conta do §3 foi executada **0 de 6 vezes** nas
SPECs anteriores — porque era regra sem portão. **Este é o portão.**

---

## 5 · O LAÇO — e ele não é opcional

```
① o BLOCO 0: REMEDIR o que a SPEC afirma, antes de codar
② o builder entrega
③ o verificador mecânico roda   →  FAIL aqui volta direto, não vai a juiz
④ 🔴 O PAINEL: N lentes DE UMA VEZ, cegas entre si, contexto limpo
⑤ funde os achados e aplica o TESTE DO PRODUTO a cada um  (§2)
⑥ conserta TUDO junto
⑦ 🔴 UM JUIZ NOVO confirma — porque CONSERTO CRIA DEFEITO
```

📊 **O ⑦ não é zelo:** na SPEC-093 o painel achou **22 defeitos, e os 6 blockers
foram todos criados pelos próprios consertos.**

🔴 **E se a SPEC tocar caminho que o segurado alcança, ou RISCO 6+:** depois do
laço, **a auditoria externa** (§6.1) — contexto novo, que não viu a execução,
recebe só a SPEC e o código pronto. 📊 Ela achou, duas vezes, o que o laço não
achou.

---

## 6 · O QUE TODA SPEC EXIGE DE VOCÊ

```
🔴 o BLOCO 0 REMEDE tudo que a SPEC afirma.
   Se o seu número for diferente, o SEU vence. Meça, mostre, e devolva.
   📊 Na última leva isso derrubou NOVE afirmações.

🔴 toda migration lista os valores do CHECK no APPLY, e um teste TENTA gravar
   valor inválido exigindo que o banco RECUSE.
   ⚠️ Uma SPEC pediu um valor que o CHECK não tinha, e isso só apareceu no
   meio da execução.

🔴 toda tabela nova: `company_id` + RLS + FILTRO NO CÓDIGO + teste com DOIS
   tenants. O backend usa service role — RLS sozinha não protege nada.

🔴 todo guarda novo tem LINHA DE CONTROLE: prove que ele CONSEGUE ficar
   vermelho. Restaure por CÓPIA, nunca por `git checkout`.

🔴 mexeu em `app/`, `middleware.ts`, `next.config.js` ou env?
   `npm run test:rotas-montam` + `next start` + UMA requisição a `/api/…`
   ⚠️ arquivo estático responde 200 com o roteador morto.

🔴 o relatório traz QUANTAS VEZES a bateria rodou. A query está no template.

🔴 **depois de consertar QUALQUER número, caminho ou faixa: `grep` do valor
   ANTIGO no arquivo inteiro.** Qualquer sobrevivente é defeito.
   📊 Em 02/09 isso achou **três** cópias vencidas em UM comando, segundos
   depois de um juiz completo ter passado. ⚠️ **O conserto acerta o que o JUIZ
   lê — tabela, gate, referência — e deixa a cópia velha no que o EXECUTOR lê.**

🔴 **e se um contador já envelheceu duas vezes, tire-o da prosa e escreva o
   COMANDO que o produz.** Mata a classe, em vez de remendar a instância.
```

---

## 7 · 🔴 QUANDO PARAR — e é tão importante quanto quando continuar

**Depois de cada rodada, classifique o que sobrou** (§9.1):

```
🔴 MATERIAL — continua
   segurança · isolamento entre corretoras · integridade · Core
   critério de aceite não provado · regressão · falha real de serviço

⛔ NÃO MATERIAL — vira PENDÊNCIA e a execução AVANÇA
   estilo · micro-refactor · nome melhor · abstração mais bonita
   documentação que ninguém precisa · dívida sem efeito hoje
```

🧑 **A regra do Founder, escrita:**

```
2h → 93/100 sem defeito material   é MELHOR que   24h → 95/100 de polimento
6h → 99/100 fechando risco no Core é MELHOR que   2h → 85/100 com fragilidade
```

### E se estourar a faixa que você declarou

⚠️ **Não para automaticamente.** Responda por escrito:

```
🔴 POR QUE CONTINUAR?
   o que falta · que risco fecha · que gate fecha · que evidência falta
```

**Se a resposta for só *"dá para melhorar mais"* → pendência, e siga.**

### 🔴 E se travar sem avançar

```
o MESMO blocker em duas rodadas, sem evidência nova
nenhum gate mudou de estado
o patch é feito e desfeito
```

**Pare. Registre o que está provado e o que já se tentou. Abra contexto fresco e
troque a ESTRATÉGIA.** ⛔ Travamento nunca transforma FAIL em PASS.

---

## 8 · A LICENÇA DE AUTONOMIA

**Não pare para perguntar.** Travou mais de **30 minutos**, ou achou contradição
na SPEC:

```
1. escolha o caminho MAIS CONSERVADOR
2. anote numa CAIXA DO FOUNDER no fim do relatório
3. e SIGA
```

**As únicas coisas que param você de verdade:**

```
🔴 risco de perda de dado
🔴 qualquer coisa que possa mandar mensagem para segurado ou seguradora
🔴 P0 de segurança ou vazamento entre corretoras
🧑 ação física do Founder — variável de produção, deploy, papel de pessoa
```

---

## 9 · COMO REPORTAR

Um relatório por SPEC, em `docs/canon/reports/`, com o template do canon.
🔴 **E ele ABRE com o EXECUTION CARD.** Relatório sem card = SPEC não fechada.

E no fim de cada um:

```
🧑 CAIXA DO FOUNDER    o que você decidiu sozinho e ele precisa saber
📊 A BATERIA           quantas rodadas, quanto tempo, que fração do relógio
🔴 O QUE FICOU ABERTO  com o que destrava cada coisa
```

Depois: **atualize o `INDICE-DE-SPECS.md`** — mova a SPEC para FEITAS e diga qual
é a próxima.

---

## 10 · 🔴 O que eu mais quero que você leve

> **Nas últimas cinco SPECs, quem tem o contexto inteiro deste projeto escreveu
> afirmações erradas — e o executor derrubou NOVE delas.**
>
> **Quando a SPEC disser algo que você mediu diferente, a SPEC está errada até
> prova em contrário.**

E o corolário, que custou um dia inteiro: **conserto cria defeito.** Depois de
consertar, **olhe de novo — com um juiz NOVO, não com os olhos de quem
consertou.** 📊 O juiz retomado tirou **05/100** no placar deste projeto. É o
pior mecanismo que já medimos.

---

## Comece pela primeira da lista da §1.

**Preflight → EXECUTION CARD → BLOCO 0 → executar.**
