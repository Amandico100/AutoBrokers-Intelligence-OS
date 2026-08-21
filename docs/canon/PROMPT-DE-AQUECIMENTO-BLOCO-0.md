# PROMPT DE AQUECIMENTO — o chat que vai executar as SPECs 083 e 084

> **Como usar:** copie tudo entre as linhas `━━━` e cole como **primeira mensagem**
> de um chat novo, na pasta `AutoBrokers-Opus-Exec`.
>
> ⚠️ **Este prompt NÃO manda executar nada.** Ele manda **auditar, conferir e
> responder**. A execução do BLOCO 0 é liberada depois, pelo Founder, com a
> resposta na mão.

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🔴 LEIA ISTO INTEIRO ANTES DE TOCAR EM QUALQUER COISA

Você vai executar duas SPECs do **AutoBrokers Intelligence OS**. Elas custaram
**quinze rodadas de juiz crítico** para ficarem prontas e subiram de 54 para 98
pontos nesse processo. **Nesta primeira mensagem você não executa nada.**

Sua tarefa agora é **auditar, conferir e responder**. Só depois de o Founder ler
a sua resposta e alinhar o que estiver torto é que a execução é liberada.

---

## ⛔ AS PROIBIÇÕES — antes de tudo, porque quebrar qualquer uma é P0

```
1. É PROIBIDO LIGAR OS AGENTES DE ATENDIMENTO.
   Eles estão 100% desligados. A única forma de ligar é a corretora clicar
   no botão "Ligar Agente" no dashboard. Você NUNCA liga.

2. É PROIBIDO ENVIAR MENSAGEM para qualquer número, em qualquer canal.
   Se um teste precisar disso, PARE e peça ao Founder — e só com a
   AMANDUS SEGUROS, avisando antes.

3. É PROIBIDO ESCREVER NO BANCO. Somente leitura (SELECT).
   Nada de INSERT, UPDATE, DELETE, DDL ou migration sem manifesto aprovado.

4. É PROIBIDO ACESSAR PORTAL DE SEGURADORA.
   Nem para "conferir uma tela". Entrada demais nos portais nos bloqueia.

5. É PROIBIDO IMPRIMIR SEGREDO — token, senha, chave, CPF completo.
   Apenas presença/ausência. CPF sempre mascarado.

6. É PROIBIDO FAZER MERGE NA `main` sem o gate final da SPEC.
```

⚠️ **Se qualquer tarefa parecer exigir uma dessas, você entendeu errado a tarefa.**
Pare e pergunte.

---

## 1. O QUE É O PRODUTO, EM DEZ LINHAS

**AutoBrokers.ai** é um SaaS multi-tenant para **corretoras de seguros**. Não é
chatbot com ferramentas: é o **sistema operacional de trabalho da corretora**.

O pedaço que interessa a você é o **acionamento de assistência**:

```
O segurado chama a corretora no WhatsApp: "minha máquina de lavar quebrou".
A atendente (agente de IA) coleta os dados.
O CORREDOR conversa com a URA da seguradora, também por WhatsApp,
   passo a passo, respondendo às telas dela.
Volta com o PROTOCOLO, a DATA e o PERÍODO da visita técnica.
```

Um **corredor** (ou *playbook*) é a receita de como conversar com a URA de uma
seguradora para um serviço. Uma **rota** é `seguradora × ramo × serviço` — por
exemplo `allianz × residencial × maquina_de_lavar`.

📊 **Existem 62 rotas.** Hoje **uma** funciona ponta a ponta.

---

## 2. ONDE ESTAMOS — e este é o fato que organiza tudo

📊 **19/08/2026, 16:35 BRT.** O Founder conduziu, ao vivo e com cliente real, um
acionamento de máquina de lavar na Allianz. O corredor conversou com a URA e
voltou com o **protocolo 52955490 em 5 minutos e 55 segundos**. Zero
`needs_human`, zero retentativas, 19 das 22 respostas por âncora determinística.

**Funcionou.** E a auditoria depois mostrou que, mesmo funcionando, **ela tem
quatro furos que ninguém viu** — o cliente não recebeu a data, a senha chegou um
segundo tarde, e um teste estava vermelho. **Todos cobertos por cima**, pelo
cérebro adaptativo ou pela própria atendente.

> 🔴 **Furo coberto é furo que ninguém vê.** Construir 61 rotas assim seria
> repetir isso 61 vezes.

Daí as duas SPECs.

---

## 3. AS DUAS SPECs, EM UMA FRASE CADA

| SPEC | o que entrega | o que NÃO faz |
|---|---|---|
| **083 — A RÉGUA** | a ferramenta que dá **nota 0–100** a qualquer rota, sozinha, sem LLM; o **corpus** de telas reais versionado; e o **gate** | não muda nenhum corredor |
| **084 — A FÁBRICA** | leva as **62 rotas** ao patamar da que funciona, uma por vez, com juízes | não inventa corredor sem evidência |

📊 Aplicada à rota que funciona, a régua dá **73 de 100** — e nomeia os cinco
pontos que faltam. Eles são as cinco primeiras entregas da 084.

---

## 4. 🔴 A CULTURA — e ela vale mais que as duas SPECs

Estas SPECs passaram por **quinze rodadas de juiz crítico**. Em cada uma, o
defeito foi achado por **alguém que rodou uma query** — nunca por alguém que leu.
Os defeitos trocaram de dono quatro vezes:

```
a SPEC afirmando sem medir ....... a árvore · o gate de 95 · os "3 itens"
o JUIZ prescrevendo sem medir .... o limiar 25 · o `+10` · o teto · o hapax
o desenho novo sem custo somado .. a triagem que lia 2,4% da fila
o gate cujo alvo se movia ........ 2.638 → 2.589 conforme o trabalho anda
```

### As seis regras que sobreviveram, e você vai ser cobrado por elas

```
1. MEDIR VENCE DEDUZIR.
   E toda bateria precisa de uma LINHA DE CONTROLE — a rodada que repete
   a condição anterior. É ela que dá direito à conclusão.

2. UM GUARDA QUE NÃO PODE FICAR VERMELHO NÃO GUARDA NADA.
   E um que nunca fica verde é bloqueio. Prove os DOIS sentidos.

3. 📊 = MEDIDO (exige data, fonte e a query). 💭 = ILUSTRATIVO (nunca
   citável como fato). Número sem marca, em documento novo, é defeito.

4. NENHUMA REGRA ENTRA SEM A QUERY QUE A PRODUZIU — inclusive as que o
   juiz escrever. Prescrição sem medição você REPRODUZ antes de aplicar.

5. BUILD VERDE NÃO É PROVA DE QUE A APLICAÇÃO SOBE.
   Rota que responde 200 vale mais que build de 287 rotas.

6. NÃO CRIAR MOTOR PARALELO. Consolidar e migrar antes de duplicar.
   Um segundo normalizador, um segundo mascarador, um segundo script —
   os dois divergem no dia em que um for corrigido.
```

### E três episódios que você deve conhecer, porque vão se repetir

📊 **O `numero_residencia`.** Um passo exigia a frase *"informe o número da
residência"*. Ela tem **ZERO ocorrências em 28.096 eventos** — a URA escreve
*"me CONFIRME o número"*. Sobreviveu semanas porque **quem escreveu a âncora não
foi ao acervo conferir**.

📊 **A rota vazia que tirava 49/100.** A primeira versão da régua podia ser
enganada: bastava chamar uma função de fábrica, escrever um teste com uma chamada
ao motor e quatro comentários com a palavra CONTROLE. **Sem responder uma única
tela real.**

📊 **O `marcas_de_corretora() → 0`.** Um teste do mascarador rodou **sem banco** e
devolveu zero marcas. A conclusão tirada foi *"o mascarador tem três buracos"*.
**A última linha da saída era o controle das três primeiras** — e ninguém a leu
como tal. Com o banco ligado, era **um** buraco.

---

## 5. 🔴 COMO VOCÊ VAI TRABALHAR — subagentes e juízes, sempre

**Você não trabalha sozinho.** As duas SPECs exigem isso, cada uma na sua seção
(083 §7.5 · 084 §5.3 e §6):

```
🔍 MINERADOR / COLETOR   lê o acervo e extrai padrões e corpus
                         🔴 NÃO escreve ferramenta nem corredor

🔧 FERRAMENTEIRO / ESCRITOR   escreve o código e os testes
                         🔴 NÃO inventa padrão. Padrão que faltar volta
                            ao minerador — nunca é escrito de cabeça

⚖️ TRÊS JUÍZES           cada um com uma lente diferente
                         🔴 A LIBERAÇÃO É DELES. Você não libera o seu
                            próprio trabalho.
```

### E o laço, com as palavras do Founder

> *"O juiz falar, o executor fazer os ajustes e o juiz conferir de novo… até
> liberar de verdade. **Não pode ser feito o juiz fala, executa e acabou.**"*

```
① você entrega          ④ 🔴 O MESMO JUIZ julga DE NOVO
② o juiz julga + mede   ⑤ repete até ele liberar
③ você conserta

TETO: 3 voltas. Bateu sem liberar → `PRECISA_DE_HUMANO` com dossiê.
🔴 NUNCA um verde forçado.
```

---

## 6. 📋 SUA TAREFA AGORA — auditoria e alinhamento, ZERO execução

### Passo 1 — Preflight

```bash
git rev-parse --show-toplevel     # deve ser AutoBrokers-Opus-Exec
git branch --show-current
git rev-parse HEAD                # registre
git status --short                # deve estar limpo
```

### Passo 2 — Leia, nesta ordem

```
1. CLAUDE.md                                  as regras invioláveis
2. docs/canon/EXECUTION-MASTER-PLAN.md        onde estamos
3. docs/canon/GLOSSARIO.md                    um termo, uma definição
4. docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md antes de tocar em ura_maps
5. docs/canon/specs/SPEC-083-a-regua-do-corredor.md    INTEIRA
6. docs/canon/specs/SPEC-084-a-fabrica-de-rotas.md     INTEIRA
7. docs/canon/MIGRATIONS-AUTHORITY.md         antes de qualquer SQL
```

### Passo 3 — Confira no banco, você mesmo

Banco Supabase, project_id `dcajcvlzcjbmyapmklil`. **Somente SELECT.**

Confira estes números das SPECs e diga se batem:

```
observed_events: total, direction='in', sessões, seguradoras, corretoras
o pool de telas com ≤3 sessões na zona URA
o percentual de eventos `in` posteriores à tela de transferência
```

### Passo 4 — Confira no código

```
backend/app/services/corridor_playbooks.py       os 14 corredores
backend/app/services/insurer_dispatch_service.py o motor
backend/app/services/atlas/templater.py:1381     templatize()
backend/scripts/                                 medir_rota.py existe?
```

---

## 7. ❓ AS QUINZE PERGUNTAS QUE VOCÊ TEM DE RESPONDER

**Responda uma por uma, numeradas, com 📊 e a query/arquivo onde couber.**
Resposta sem evidência não conta.

### Sobre o produto e o estado

1. **O que é uma "rota" e o que é um "corredor"?** Quantas rotas existem, e de
   onde sai esse número? (📊 mostre a conta)
2. **Qual é a única rota validada em produção**, e o que exatamente ela provou?
3. **Quantas telas de URA existem no acervo**, de quantas seguradoras e de quantas
   corretoras? (📊 a query)

### Sobre a SPEC-083

4. **O que a régua entrega, e o que ela explicitamente NÃO faz?**
5. **Quais são os cinco eixos da rubrica e quanto vale cada um?** Por que o eixo
   B vale mais que os outros?
6. **Por que a rota validada tira 73 e não 100?** Nomeie os cinco itens que
   faltam. (📊 estão na SPEC — cite a seção)
7. **O que é a "rota vazia que tirava 49/100"** e o que foi feito para impedir
   isso?

### Sobre a SPEC-084

8. **Por que a ordem do trabalho é "por profundidade" e não por seguradora nem
   por ramo?** Explique com a metáfora da árvore.
9. **O que é a "zona URA" e a "zona HUMANO"?** 📊 Que percentual do acervo é zona
   humana, e o que aconteceria se não separássemos?
10. **Por que o gate de triagem NÃO pode reprovar uma seguradora pelo número?**
    (📊 a resposta envolve dispersão entre corpora limpos)
11. **O que são as "8 rotas indistinguíveis"** e por que é proibido escrevê-las
    antes de criar a marca?
12. **O que o BLOCO 0 entrega, e qual é o gate dele?** Nomeie os cinco G.

### Sobre a disciplina

13. **Cite três guardas destas SPECs e diga, para cada um, como você provaria
    que ele CONSEGUE ficar vermelho.**
14. **O juiz manda você aplicar uma correção com um número que ele mediu.
    O que você faz antes de aplicar?** E por quê?
15. **Você acha que entendeu tudo?** 🔴 **Liste o que você NÃO entendeu, o que
    achou ambíguo, e o que você acha que está errado nas SPECs.** Esta é a
    pergunta mais importante das quinze. Resposta "entendi tudo" é reprovada.

---

## 8. 🔴 E TRÊS COISAS QUE VOCÊ DEVE ME DEVOLVER, ALÉM DAS RESPOSTAS

### A · Discordâncias
Se algum número não bater, se alguma instrução for impossível, se duas seções se
contradisserem — **diga**. As SPECs erraram quinze vezes; podem errar a
décima sexta. 📊 Traga a medição.

### B · O que falta para você começar
Alguma credencial, algum acesso, alguma decisão do Founder? **Nomeie agora**, não
no meio da execução.

### C · O seu plano do BLOCO 0, em 15 linhas
Na ordem em que você faria, dizendo **onde vai usar subagente e onde vai chamar
juiz**. Não é para executar — é para o Founder ver se está alinhado.

---

## 9. ⛔ O QUE VOCÊ NÃO FAZ NESTA RODADA

```
✗ não escreve código          ✗ não roda migration
✗ não altera SPEC             ✗ não commita nada
✗ não gera corpus             ✗ não toca em playbook
✗ não liga agente             ✗ não envia mensagem
```

**Você lê, confere no banco e no código, e responde as quinze perguntas.**

O Founder vai levar a sua resposta para o chat que escreveu as SPECs, alinhar o
que estiver torto, e voltar com a liberação do BLOCO 0.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---

## 📌 NOTA PARA O FOUNDER — o que eu vou olhar na resposta dele

Quando você trouxer a resposta, eu vou verificar seis coisas:

| # | o que eu procuro | por que importa |
|:-:|---|---|
| 1 | Ele **rodou as queries** ou só repetiu os números da SPEC? | Se repetiu, não vai medir durante a execução também |
| 2 | A pergunta **15** — ele listou dúvidas de verdade? | "Entendi tudo" é o sinal mais perigoso |
| 3 | Ele entendeu que **o juiz libera, não ele**? | É a regra que você mais insistiu |
| 4 | Ele entendeu que **o número não reprova** — quem reprova é a leitura? | É o achado mais difícil das 15 rodadas |
| 5 | Achou alguma **discordância real**? | Um executor que não discorda de nada não leu |
| 6 | O plano dele do BLOCO 0 tem **subagente e juiz nos lugares certos**? | Se não tiver, ele vai trabalhar sozinho |

🔴 **Se ele falhar em 1, 2 ou 3, eu recomendo NÃO liberar o BLOCO 0** e mandar
uma segunda rodada de alinhamento. É mais barato que consertar corpus errado.
