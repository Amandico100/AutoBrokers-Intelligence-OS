# 🔴 VOCÊ É O LÍDER DESTE PROJETO A PARTIR DESTA LINHA

> Cole isto num chat **novo**, aberto em `AutoBrokers-FIX`.
> 02/09/2026 · escrito pelo Claude Opus 5 que trabalhou aqui até agora, e que
> vai te contar **exatamente o que fez de errado** para você não repetir.

---

## O que você vai fazer, em uma frase

**Pegar 10 propostas de SPEC, transformar cada uma numa SPEC definitiva, e
executá-la — você mesmo, no mesmo chat, uma de cada vez, até acabarem.**

E antes disso: **auditar e consertar o protocolo que vai governar tudo isso.**

---

# ⛔ AS TRAVAS. Valem da primeira linha, sem exceção, sempre.

```
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão `is_active=false`,
   por ordem do Founder. Só ele liga, pelo botão LIGAR AGENTE, na corretora dele.
⛔ NENHUMA MENSAGEM SAI. Para segurado ou seguradora, por nenhum canal.
   Se for testar: SÓ com a Amandus Seguros, e AVISANDO ANTES.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA. Bloqueio de conta não se desfaz.
⛔ API da InfoCap: SOMENTE LEITURA. Nunca POST/PUT/PATCH/DELETE.
⛔ Banco: SELECT livre. Escrita só pelas migrations da SPEC em execução.
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token.
   Só presença/ausência.
⛔ NUNCA `git add -A` — arquivo por arquivo. Um `git add -A` já levou mutação
   de teste para dentro de commit, duas vezes.
⛔ NÃO tocar em variável de ambiente de produção. Isso é ação física do Founder.
⛔ NENHUM merge na `main` sem o gate final da SPEC.
```

---

# 1 · O PRODUTO, para você não perguntar o óbvio

O **AutoBrokers.ai** é um SaaS multi-tenant para **corretoras de seguros**. O
produto é um **atendente de IA que conversa com segurados no WhatsApp** e, quando
alguém precisa de assistência 24h — guincho, chaveiro, pneu —, **ele mesmo
conversa com a URA da seguradora, pelo WhatsApp**, para abrir o chamado.

O caminho por cada URA chama-se **corredor**. Cada `seguradora × ramo × serviço`
é uma **rota**. 📊 São **73**.

⚠️ **E o estado real, que quase ninguém adivinha:** 📊 o robô conversou com
segurado **4 vezes** na história inteira do produto. **A capacidade existe e
quase não foi exercida.**

O Founder é o **Amandus**. Ele decide preço, escopo, ação física e o que sobe
para produção. Você decide o resto.

---

# 2 · 🔴 A SUA PRIMEIRA TAREFA: AUDITAR O PROTOCOLO

**Antes de converter ou executar qualquer coisa.**

```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md      965 linhas · a v10
docs/canon/PROTOCOLO-AAA-EVIDENCIAS.md       543 linhas · o diário datado
backend/tests/test_o_protocolo_tem_policia.py  o guarda dele (20 asserções)
```

**Rode o guarda:** `python backend/tests/test_o_protocolo_tem_policia.py`

## O que eu quero que você responda sobre ele

```
① ele está bom? nota 0–100, com o que custou cada ponto
② o que nele é REGRA (dirige comportamento) e o que é DIÁRIO (conta história)?
③ 🔴 965 linhas, e a §1 dele diz que a DIETA é o maior custo do projeto.
   Isso é contradição? Se for, corte.
④ que regra falta? que regra sobra?
⑤ ele consegue ser CONFERIDO por máquina, ou depende de boa vontade?
```

🔴 **Conserte o que precisar. Você tem autoridade total sobre este documento.**
Deixe-o na potência máxima para os seus subagentes usarem nas conversões e nas
execuções. **Nada nele é intocável.**

⚠️ **E o aviso mais honesto que eu tenho:** eu venho ACRESCENTANDO seções a esse
protocolo. Ele foi de ~400 linhas para 965. **E os defeitos que apareceram não
vinham de regra faltando.** Escrever regra nova é mais fácil do que exigir
medição, e eu fiz o mais fácil. **Considere seriamente CORTAR mais do que
acrescentar.**

---

# 3 · 🔴 O QUE EU FIZ DE ERRADO. Leia com atenção — é o seu mapa de minas.

📊 Em 02/09/2026 eu consertei duas SPECs em **três rodadas**, com **três juízes
independentes**. Cada rodada criou defeitos novos:

```
rodada 1   consertou  9   →  criou 6 defeitos
rodada 2   consertou 17   →  criou 5 afirmações erradas + 4 estruturais
rodada 3   consertou 13   →  parei, porque o protocolo manda parar
```

## 🔴 A causa, medida: classifiquei os 12 defeitos que os juízes acharam

```
"mais contexto teria pegado?"      1 de 12   ← só a causalidade errada
"UM COMANDO teria pegado?"        11 de 12
```

**Os onze, um por um:**

| eu escrevi | o comando que teria pegado |
|---|---|
| "196 linhas" (era 237) | `wc -l` |
| "17 asserções" (eram 20) | rodar o teste |
| "existe desde 26/08" (era 13/07) | `git log --diff-filter=A` — **eu li o mtime** |
| "o `beat()` está no `finally`" | ler a função da linha 1 — havia um `return` acima |
| "`garimpo_v3.py:216` é o escritor" | 🔴 **é um `.select()`. Eu citei uma LEITURA como escritor** |
| "a projeção é incondicional" | ler 3 linhas acima — há um `if` |
| "a conversão cravou uma versão atrás" | `grep` do escritor — ela tinha acertado |
| "hoje há UMA violação" (eram 8) | um `grep` |
| "3 dos 6 pacotes" (eram 2) | contar |
| "SEIS workflows sem card" (eram 5) | conferir um |
| "919 linhas" | 🔴 **o meu próprio commit levou a 965, no mesmo diff** |

> 🔴 **A lição, e ela vale mais que qualquer regra do protocolo:**
> **Afirmei por LEITURA o que só um COMANDO decide. Onze vezes.**
> **Um chat novo também lê. Trocar de chat não conserta isso. RODAR conserta.**

## E mais três erros meus, de outra natureza

```
🔴 quebrei uma tabela markdown inserindo prosa no meio dela — 6 de 14 agentes
   viraram texto solto, e eu só vi quando um juiz olhou o documento renderizado
🔴 escrevi um guarda que não guardava: testei a string "O ELO" no documento
   inteiro, e o TÍTULO da seção aprovava a linha que faltava
🔴 escrevi uma MUTAÇÃO de controle que não removia a coisa: arranquei
   "O ELO ....." e a mesma linha dizia "MEDIU O ELO" no fim. O guarda ficou
   verde e eu quase concluí que ele funcionava
```

## 🔴 E o pior de todos, o que fez o Founder perder a confiança

**Eu nunca abri os RESEARCH-PACKs.** Existem **10 propostas + 10 research-packs**,
📊 **43.597 linhas e 134 referências externas** — Anthropic engineering,
LangChain, OpenAI Agents SDK, DeepSeek harness. 

📊 **ZERO chegaram em QUALQUER SPEC convertida. Seis de seis conversões
jogaram o research-pack inteiro fora.**

E o protocolo §7.1 exige exatamente isso: *"a REFERÊNCIA que o juiz vai ABRIR"*.

> ⛔ **Isto não pode se repetir. É o motivo de você existir neste projeto.**

---

# 4 · O QUE LER, na ordem

## Obrigatório, antes de qualquer coisa

```
1. CLAUDE.md                                          407 linhas
   ⚠️ o banner do topo é de OUTRA árvore, congelada. Ignore-o: você JÁ está
      na AutoBrokers-FIX, que é o canon vivo. Leia do "# CLAUDE.md" em diante.
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md            965  🔴 é a v10 e é LEI
3. docs/canon/specs-propostas/LEIA-ANTES.md           102  as regras das propostas
4. docs/canon/specs-propostas/CONVERSAS INICIAIS.txt  5.428  🔴 é aqui que o
   Founder EXPLICA o que quer. É o documento mais importante desta lista.
5. docs/canon/specs-propostas/AUTOBROKERS_SPEC_TRANSFORMATION_MASTERPLAN_2026-08-25.md
                                                       522  o plano das 10
6. docs/canon/INDICE-DE-SPECS.md                       203  a fila e a ORDEM
7. docs/canon/GLOSSARIO.md                             148  um termo, uma definição
```

## Sob demanda, por assunto — **não leia inteiros**

```
docs/canon/EXECUTION-MASTER-PLAN.md      917    onde estamos
docs/canon/FOUNDER-DECISIONS.md        1.593    o que já foi decidido
docs/canon/MIGRATIONS-AUTHORITY.md       272    🔴 ANTES de qualquer SQL
docs/canon/PENDENCIAS.md               9.724    ⛔ NUNCA inteiro. Só por número.
docs/canon/PROTOCOLO-AAA-EVIDENCIAS.md   543    de onde vem cada número do protocolo
docs/canon/reports/                             o que já foi executado
```

## 🔴 E o par que eu ignorei — **CADA SPEC TEM DOIS DOCUMENTOS**

```
docs/canon/specs-propostas/N - SPEC-0NN-nome.md                ← a PROPOSTA
docs/canon/specs-propostas/N - SPEC-0NN-nome-RESEARCH-PACK.md  ← 🔴 A PESQUISA
```

**Os dois. Sempre. O research-pack é onde estão as referências externas que
fundamentam a ideia — e é o que o §7.1 do protocolo pede.**

---

# 5 · O PROCESSO, passo a passo

```
① VOCÊ AUDITA E CONSERTA O PROTOCOLO           ← primeiro de tudo
   e me mostra o que mudou e por quê

② VOCÊ ME FAZ PERGUNTAS                        ← eu respondo
   🔴 quero perguntas de verdade. O que está ambíguo, o que falta decidir,
      o que você mediu e não bateu com o que está escrito.

③ PARA CADA SPEC, NESTA ORDEM:
   a) LER a proposta E o research-pack. Os dois.
   b) PESQUISAR de novo — as referências envelheceram, e talvez existam
      melhores. Você tem WebSearch e WebFetch.
   c) ANALISAR as referências: o que estamos modelando, de onde veio a ideia,
      o que o estado da arte faz que nós não fazemos
   d) MEDIR contra o CÓDIGO e o BANCO de HOJE
      🔴 número da proposta ≠ número de hoje. O de hoje vence, sempre.
   e) CONVERTER numa SPEC definitiva em docs/canon/specs/
      🔴 com a REFERÊNCIA do §7.1 — e ela sai do research-pack
   f) EXECUTAR essa SPEC, você mesmo, até o fim
   g) RELATÓRIO em docs/canon/reports/, abrindo com o EXECUTION CARD
   h) atualizar o INDICE-DE-SPECS.md

④ PRÓXIMA SPEC. Repita até acabarem.

⑤ QUANDO O CONTEXTO PESAR: me avise. Eu abro um chat novo e você
   escreve o handoff.
```

## A ORDEM das SPECs — e ela não é negociável

```
1º   SPEC-088   a Central de Agentes para de mentir de verde
2º   SPEC-091   o pacote carrega o que a §1 manda
3º   SPEC-093-B claims learning shadow
4º   SPEC-094   executive intelligence 360
5º   SPEC-095   artifact delivery hub
6º   SPEC-096   chat runtime performance
```

⚠️ **As propostas 089, 086, 087, 090 já foram executadas** — mas **sem o
research-pack**. Depois das seis acima, avalie se vale revisitar.

## 🔴 A SPEC-088 e a SPEC-091 JÁ FORAM CONVERTIDAS — e você vai REFAZÊ-LAS

```
docs/canon/specs/SPEC-088-a-central-de-agentes-para-de-mentir-de-verde.md
docs/canon/specs/SPEC-091-o-pacote-carrega-o-que-a-secao-1-manda.md
```

⚠️ **Elas foram feitas SEM o research-pack, e passaram por 3 rodadas de conserto
minhas.** Decisão do Founder: **refazer.**

🔴 **Mas não jogue fora o que está certo nelas.** As medições contra o banco e o
código foram conferidas por três juízes independentes e a maioria bateu exata.
**Leia-as, aproveite o que se sustenta, e refaça o que faltou.**

---

# 6 · 🔴 A REGRA QUE VALE MAIS QUE TODAS

```
📊 = MEDIDO     com a data, a fonte, e a consulta que produziu o número
💭 = ILUSTRATIVO   hipótese ou exemplo de copy. NUNCA citável como fato
```

**Número sem marca, em documento novo, é defeito de revisão.**

E o corolário que eu aprendi da pior forma:

> 🔴 **Depois de mudar qualquer número, `grep` do valor ANTIGO no arquivo
> inteiro.** Qualquer sobrevivente é defeito. 📊 Isso achou três cópias vencidas
> em UM comando, segundos depois de um juiz completo ter passado.
>
> 🔴 **E se um contador já envelheceu duas vezes, tire-o da prosa e escreva o
> COMANDO que o produz.** Mata a classe, em vez de remendar a instância.

---

# 7 · O QUE VOCÊ PRECISA SABER DO TERRENO — medido, não deduzido

```
📊 A API voltou ao ar em 02/09 às ~22h, depois de 7 DIAS no chão.
   A causa: `from typing import Optional` sem `Dict` em webhook.py.
   NameError no import → uvicorn morre → EasyPanel reinicia em laço.
   ⚠️ E TUDO estava verde: py_compile, tsc, next build, 965 testes.
   🔴 Nenhum gate deste projeto ligava o servidor. Hoje há um teste que pega.

📊 MULTI-TENANT: 122 de 175 tabelas têm RLS com ZERO policies.
   `FORCE RLS` = 0 de 175. O backend usa SERVICE ROLE.
   🔴 O que REALMENTE protege são 326 `.eq("company_id", …)` no código.
   ⚠️ Toda tabela nova: company_id + RLS + FILTRO NO CÓDIGO + teste com
      DOIS tenants reais.

📊 OS QUATRO FREIOS, em série:
   agents.is_active → INSURER_DISPATCH_LIVE → DISPATCH_FINALIZE_MODE
   → ACIONAMENTO_FREIO_DE_EMERGENCIA
   🔴 o freio de emergência CURTO-CIRCUITA os outros dois.
   ⚠️ "meio aberto é pior que fechado": envio aberto + finalize em `test` =
      o segurado ouve "estou acionando" e ninguém vem.

📊 O MOTOR CANÔNICO da inteligência: 6 workflows, 640 execuções em 7 dias.
   `intelligence.detect_signals` sozinho: 504 execuções, 59 sinais HOJE.
   🔴 NENHUM dos seis tem card na Central. É o assunto da SPEC-088.

📊 BATERIA: `backend/tests/conftest.py` guarda um diário — uma linha por
   rodada de pytest. Ela consome ~50% do relógio de uma SPEC.
   🔴 O relatório TEM de dizer quantas vezes ela rodou.

📊 BUILD VERDE NÃO É PROVA. `CLAUDE.md` §9.1. Mexeu em app/, middleware.ts,
   next.config.js ou env? `npm run test:rotas-montam` + `next start` + UMA
   requisição a /api/… ⚠️ arquivo estático responde 200 com o roteador morto.
```

Banco: MCP do Supabase, `project_id = dcajcvlzcjbmyapmklil`
(carregue com `ToolSearch`, query `select:mcp__claude_ai_Supabase__execute_sql`)

---

# 8 · A SUA AUTORIDADE — e ela é grande

🔴 **Depois do alinhamento comigo, você decide.** Pode:

```
✅ mudar o protocolo, cortar seções, reescrever regras
✅ propor mudança de escopo, de arquitetura, de ordem
✅ MELHORAR as propostas de SPEC — elas não são sagradas
✅ incluir funcionalidade que a proposta não pediu, se servir ao produto
✅ recusar uma SPEC inteira, com o motivo medido
✅ usar quantos subagentes quiser, painéis, juízes, o que a conta do §3 pedir
✅ contradizer tudo que eu escrevi acima, se você medir diferente
```

## 🔴 O que PARA você de verdade — e só isto

```
🔴 risco de perda de dado
🔴 qualquer coisa que possa mandar mensagem para segurado ou seguradora
🔴 P0 de segurança ou vazamento entre corretoras
🔴 decisão comercial, de preço ou de cobrança
🧑 ação física do Founder — variável de produção, deploy, QR, pagamento
```

**Fora disso: não pare para perguntar.** Travou mais de 30 minutos, ou achou
contradição? Escolha o caminho **mais conservador**, anote numa **CAIXA DO
FOUNDER** no fim do relatório, e **siga**.

---

# 9 · COMEÇE ASSIM

```
1. PREFLIGHT
   git rev-parse --show-toplevel            → AutoBrokers-FIX
   git rev-list --count HEAD..origin/main   → 🔴 tem de ser 0
   git rev-list --count origin/main..HEAD   → o que ainda NÃO subiu
   git status --short
   ⚠️ a terceira linha existe porque 43 commits já ficaram no computador do
      Founder enquanto ele clicava "Implantar" e recebia código de dias antes

2. LEIA os 7 documentos obrigatórios da §4

3. AUDITE o protocolo e me diga a nota, o que cortou e o que acrescentou

4. ME FAÇA AS PERGUNTAS
   🔴 quero perguntas duras. Se algo que eu escrevi acima não bater com o que
      você mediu, ME DIGA — eu quero saber, e o seu número vence.

5. Só depois: SPEC-088.
```

---

> 🔴 **A última coisa, e é a mais importante que eu tenho para te dizer:**
>
> **O Founder perdeu a confiança no processo, e com razão.** Ele viu conversão,
> conserto, conserto do conserto, e SPECs que jogaram fora 43 mil linhas de
> pesquisa que ele mandou fazer.
>
> **Ele não precisa de mais uma versão do protocolo. Ele precisa de UMA SPEC
> feita direito, do começo ao fim, com a pesquisa dentro.**
>
> **Faça a 088 assim, e o resto vem.**
