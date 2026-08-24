# PROTOCOLO AUTOBROKERS AAA

> **Como se monta e se governa uma equipe de agentes no AutoBrokers.**
>
> Não diz **o que** construir — isso é a SPEC. Diz **como construir, julgar e
> autorizar a entrega**, e **quando parar**.
>
> v3 · 24/08/2026 · vale para **toda** SPEC, execução, ideia nova, incidente e
> agente da Central.
>
> ⚠️ **A v1 reprovou por sete blockers. A v2, por mais cinco — e dois deles o
> próprio conserto abriu.** O pior da v1: a conta dava **nove agentes para um
> comentário de coluna** e **zero para 117 commits em produção**. O pior da v2:
> ela isentava do piso a única migration de vazamento entre corretoras do
> repositório. **As duas voltas estão na §11, com o que mudou e por quê.**

---

## 0. A REGRA DE UMA LINHA

> ## Nada entra como pronto sem sobreviver a uma cadeia independente de provas.
> ## E nada trava o projeto por um defeito que não muda o produto.

**As duas metades têm o mesmo peso.** A primeira sozinha produz um sistema que não
entrega. A segunda sozinha produz um sistema que entrega lixo.

---

## 1. 🔴 O TESTE DO PRODUTO — a regra que decide se algo é blocker

**Antes de consertar qualquer achado, uma pergunta:**

```
Se eu consertar isto, muda UM BYTE do que chega:
   · ao SEGURADO       (mensagem, protocolo, prazo, cobrança)
   · à CORRETORA       (tela, relatório, alerta, decisão)
   · ao BANCO          (dado gravado, estado, integridade)
   · ou à SEGURANÇA    (acesso, isolamento, vazamento)

SIM  →  é BLOCKER. Conserta, e o laço continua.
NÃO  →  é PENDÊNCIA. Registra, e SEGUE.
```

📊 **Por que esta regra existe.** Numa execução real de 23–24/08/2026, o laço de
juiz rodou três voltas. Os primeiros achados mereciam cada minuto, e os três estão
no relatório da SPEC-084.2, verbatim:

- *"um carro no **km 42 de rodovia**, com 'em frente ao posto de gasolina' no
  endereço, fazia o produto enviar `rb_InformacoesLocal="6"` = **LOCAL SEGURO** à
  seguradora"* (`SPEC-084.2-EXECUTION-REPORT.md:231-237`)
- *"O produto dizia ao segurado da geladeira que **a peça é por conta dele**"* —
  quando a URA da yelum diz, em eletrodomésticos, *"coberto a mão de obra E PEÇAS"*
  (`:245-250`)
- a promessa de *"você vai receber um SMS/link com a previsão de chegada"* saindo
  de zero para **dez rotas** — com `azul 0/321 · mapfre 0/75 · porto 0/521 ·
  tokio 0/70 · yelum 0/607` telas de lastro (`:299-311`)

**Os três passam no teste do produto.** O que veio depois, cada vez menor, era
redação de relatório — e redação de relatório não chega a segurado nenhum.

⚠️ **O que esta regra NÃO faz.** Ela não teria encerrado o laço na primeira volta:
os blockers da volta 1 eram legítimos, e o §6 manda consertar e julgar de novo. 📊 O
laço real acabou na volta 3, que é onde as portas da §6 também o põem. **O ganho
medido é menor e é outro: ela impede a escalada — a segunda e a terceira passada
gastas em coisa que não muda byte nenhum.**

### 🔴 E quem drena a pendência — porque uma válvula que só enche é um aterro

📊 `PENDENCIAS.md` tem **8.400 linhas** e **~328 registros abertos**, e o próprio
arquivo admite que o índice mente: *"quem confiar no índice vai reexecutar trabalho
pronto"*. **A §1 manda tudo para lá e não dizia quem tira.**

```
🔴 TODA SPEC QUE COMEÇA FECHA OU RE-JUSTIFICA AS PENDÊNCIAS QUE ELA TOCA.
   O investigador as lista no início; o relatório diz de cada uma:
   FECHADA (com a prova) · CONTINUA (com o que destrava, novo) · MORREU
   (a razão dela deixou de existir — e isso conta como fechada)

⚠️  O que a SPEC NÃO toca continua lá, e tudo bem. O aterro cresce por
   pendência órfã de dono, não por pendência registrada.
```

⚠️ **E o contrário também é proibido.** *"Isto é pequeno"* não é argumento. **A
única pergunta é se muda o produto.** Um erro de uma letra numa âncora muda o
produto; uma reescrita elegante de 200 linhas que não muda comportamento nenhum,
não.

---

## 2. DUAS CONTAS, NÃO UMA

🔴 **O RISCO diz SE precisa de juiz e quão hostil ele é. A SUPERFÍCIE diz DE
QUANTAS PESSOAS.** São perguntas diferentes, e somá-las produz um número que não
responde nenhuma das duas.

> 📊 **Foi exatamente esse o defeito da v1.** Neste produto — um atendente de
> seguros que vive no WhatsApp — o alcance está quase sempre no máximo: 26 das 66
> SPECs trazem mensagem, corredor, portal ou atendimento no nome do arquivo. Uma
> conta feita só de alcance é **constante**, e uma constante não decide nada.

### 2.1 O RISCO — 0 a 8

```
ALCANCE          ninguém sente se der errado ......... 0
                 a corretora sente ................... 2
                 o SEGURADO sente .................... 3

REVERSIBILIDADE  🔴 mede o que FICA depois de desfazer o gesto,
                 nunca o tamanho do gesto
                 desfez, e não sobrou nada ........... 0
                 sobra dado, estrutura ou estado que
                 precisa de conserto próprio ......... 2
                 ⚠️  a LINHA no ledger de migration NÃO
                    conta: ela registra o gesto, e não
                    é o que sobrou dele
                 saiu do prédio e não volta: mensagem
                 enviada, chamado aberto, portal
                 acionado, dinheiro movido ........... 3

FREQUÊNCIA       roda raramente ...................... 0
                 roda toda semana .................... 1
                 roda em TODO atendimento ............ 2
```

⚠️ 📊 **`"é só um commit"` descreve o gesto, e a v1 pontuava o gesto.** Por isso
ela dava REVERSIBILIDADE 0 ao merge de 117 commits com migrations e código de
mensagem — o `git revert` é trivial, e o que ele deixa para trás não é.

### 2.2 A SUPERFÍCIE — 0 a 3

```
0    uma decisão, num lugar, e eu SEI APONTAR o lugar
1    um comportamento, em alguns lugares que eu consigo listar
2    vários comportamentos, ou uma peça nova
3    território que ninguém mapeou — ou um lote de trabalho que já existe
     e nunca foi julgado junto
```

🔴 **A SUPERFÍCIE tem uma pergunta, e ela é a trava:**

> **"Eu consigo apontar TODOS os lugares que isto muda?"**
> **Não consigo → SUPERFÍCIE 3.** Não saber *é* a definição de território novo.

#### 🔴 E existem DOIS "não saber" — só um deles é SUPERFÍCIE

```
NÃO SEI ONDE ISTO PEGA         →  SUPERFÍCIE 3.
                                  Território de código não mapeado: mais
                                  gente, porque alguém tem de ir ver.

NÃO SEI SE O MODELO OBEDECE    →  🔴 ISTO NÃO É SUPERFÍCIE. É PROVA.
                                  Mais gente não torna um LLM previsível.
```

🔴 **Texto que instrui um modelo — prompt, playbook, regra de conduta — pontua pelos
COMPORTAMENTOS que dirige de propósito, e sai com uma obrigação a mais, nunca com mais
gente:**

> **mostrar o modelo fazendo.** Um prompt é uma instrução, não uma garantia — **a prova
> é a saída, nunca o texto.**

⚠️ 📊 **Por que esta cláusula existe.** Sem ela, a trava daria SUPERFÍCIE 3 a
**qualquer** linha de prompt — ninguém enumera as saídas de um LLM — e duas linhas em
`prompts.py` sairiam com **nove papéis**, contra os **dois** que a mesma frase recebe
num template. **A diferença seria só onde a frase está guardada**, que é o vício que a
§2.4 existe para matar. E o custo é medido: **59 dos 456 commits de agosto/2026** tocam
`prompts.py` ou `corridor_playbooks.py`. **Uma régua que convoca red team em 13% do mês
não é régua, é pedágio.**

### 2.3 A tabela

```
                         SUPERFÍCIE 0        SUPERFÍCIE 1–2       SUPERFÍCIE 3
                         uma decisão,        alguns lugares,      território novo,
                         um lugar            que eu listo         ou lote inteiro
 ──────────────────────────────────────────────────────────────────────────────
  RISCO 0–1              🔴 ninguém.         builder              builder + juiz
  ninguém sente          Faz e pronto        + juiz               + verificador

  RISCO 2–5              builder             builder + juiz       + investigador
  a corretora sente      + juiz              + verificador        + desenhista da prova

  RISCO 6+               builder             + verificador        equipe completa
  o segurado sente,      + JUIZ DA           + desenhista         + red team
  e não volta atrás        superfície          da prova           + juiz final fresco
```

⚠️ **O orquestrador escreve as DUAS contas no relatório**, com os quatro números.
Uma nota sem eles é palpite disfarçado.

### 2.4 🔴 O PISO — por EFEITO, nunca por tipo de arquivo

```
RISCO 6 no mínimo, independente da conta:

 · qualquer coisa que ENVIE       mensagem, acionamento, chamado, cobrança
 · migration que ALTERA DADO, ESTRUTURA, TRAVA, ou QUEM PODE LER
 · autenticação, sessão, ou o filtro `company_id`
 · qualquer coisa que leia de uma corretora e escreva noutra
```

```
⚠️  A ÚNICA isenção é o COMMENT: não altera dado, nem estrutura, nem
   trava, nem permissão.   🔴 ÍNDICE E GRANT DISPARAM O PISO.
```

📊 **A v1 escrevia o piso por tipo de artefato — *"migration"* — e mandava red team
consertar um `COMMENT ON COLUMN`. 🔴 A v2, consertando isso, isentou índice e GRANT — e
abriu um buraco pior, medido neste repositório:**

- 📊 **A única migration com `GRANT` do diretório canônico é a correção de vazamento
  entre corretoras** — `20260727_03_seguranca_view_cutover.sql`, que fechou uma view
  `SECURITY DEFINER` dando `SELECT/INSERT/UPDATE/DELETE` a `anon` e `authenticated`.
  Ela não toca uma linha de dado: **muda quem PODE LER.** A isenção a fazia sair como
  *"ninguém, faz e pronto"* — num repositório onde o `CLAUDE.md` §7 diz que *"RLS sem
  policy não protege nada"*.
- 📊 **Índice é as duas coisas.** `CREATE UNIQUE INDEX` sem `CONCURRENTLY` pega
  `ACCESS EXCLUSIVE` e **trava escrita** — 274 `CREATE INDEX` nas migrations, e só
  **12** `CONCURRENTLY`. E o índice `(company_id, idempotency_key)` de `20260804_02`
  **É a fronteira entre corretoras**: *"com ele o isolamento passa a ser estrutural"*.
  **A isenção dispensava do piso o artefato que implementa um gatilho do próprio piso.**

🔴 **E a lição custou duas voltas para entrar:** exceção escrita por **tipo de
artefato** volta a errar — mesmo quando o objetivo declarado era consertar exatamente
isso. **O piso só sobrevive escrito por EFEITO.**

### 2.5 🔴 A conta vale para MUDANÇA, não para INVESTIGAÇÃO

Avaliar uma ideia, **auditar**, **mapear**, medir se algo funcionou — nada disso muda
byte nenhum: a conta dá zero, e daria zero sempre. Todos usam o elenco do **MODO
INVESTIGAÇÃO** (§7), e o que os dimensiona é a **largura** — quantas frentes
independentes — nunca o risco.

**E o que a investigação RECOMENDA é pontuado quando virar trabalho.**

⚠️ 🔴 **E isto NÃO é a mesma coisa que a dispensa da §8.** A fronteira, escrita uma
vez só, e vale para os dois lugares:

```
CONSULTA PONTUAL — a resposta cabe numa frase
   "onde está X?" · "o que essa função faz?" · "esse arquivo existe?"
   → 🔴 DISPENSADO (§8). Lê e responde. Não monta ninguém.

VARREDURA — precisa de conclusão, e a conclusão vira decisão
   "isto funcionou?" · "o que falta fechar?" · "serve para nós?"
   → MODO INVESTIGAÇÃO (§7). Elenco fixo, dimensionado pela largura.
```

### 2.6 📊 A conta, validada nos seis casos que reprovaram a v1

| caso | RISCO | SUP | v1 dava | **v2 dá** |
|---|:---:|:---:|---|---|
| trocar uma palavra numa mensagem que o cliente vê | **8** | **0** | 8 · **e 0–1 · e piso 6** — três respostas | **builder + juiz da superfície.** O juiz lê a palavra. Ninguém investiga |
| SPEC nova: corredor × URA da Porto | **8** | **3** | 8, e a §7 dava elenco fixo de 4 | **equipe completa + red team + juiz final** |
| *"vi uma técnica nova, serve para nós?"* | — | — | 0 · e 4 papéis · e "não se aplica" | **§2.5: a conta não governa.** MODO IDEIA, elenco fixo de 4 |
| P-179 · uma palavra num `COMMENT ON COLUMN` | **0** | **0** | 8 pelo piso (*"migration"*) | 🔴 **ninguém. Faz e pronto** |
| P-084-78 · três apelidos em `_SUBSERVICE_ALIASES` | **8** | **0** | 8 → nove papéis para três strings | **builder + juiz.** O juiz confere os três destinos |
| P-23 · merge da `main`, 117 commits | **8** | **3** | 🔴 **0 — "ninguém, faz e pronto"** | **equipe completa + red team + juiz final fresco** |

### 📊 E os TRÊS casos que reprovaram a v2 — a segunda validação

| caso | RISCO | SUP | v2 dava | **v3 dá** |
|---|:---:|:---:|---|---|
| `20260727_03` · o `GRANT` que fechou a view `SECURITY DEFINER` aberta a `anon` | **6** pelo piso | **1** | 🔴 **ninguém** — a v2 isentava GRANT | **builder + juiz + verificador** |
| `20260804_02` · o índice `(company_id, idempotency_key)` — a fronteira estrutural | **6** pelo piso | **1** | 🔴 **ninguém** — a v2 isentava índice | **builder + juiz + verificador** |
| duas linhas de texto em `ATTENDANCE_BASE_PROMPT` | **8** | **0** | **3** pela trava do "não saber" → nove papéis | **builder + juiz**, + a obrigação de **mostrar o modelo fazendo** |

⚠️ 📊 **E o P-179 tem validação de fora, que ninguém planejou:** o conserto real foi
feito em 16/08, **antes deste protocolo existir**, como uma linha dentro de
`20260816_01_a_carta_diz_que_pergunta_responde.sql:68` — sem juiz, sem red team, sem
bloco próprio. **O mundo já rodou a prescrição da v3, e ela estava certa.**

🔴 **O par que prova a conta é o último e o penúltimo da primeira tabela:** a v1 dava a mesma nota
(8) para três strings e para 117 commits em produção, e dava **zero** para o
segundo por outro caminho. A v2 separa os dois por SUPERFÍCIE, que é o eixo que
mede a diferença entre eles.

---

## 3. OS PAPÉIS — e só existem os que a conta pediu

```
🎯 ORQUESTRADOR      faz as duas contas, monta o time, controla o laço,
                     classifica o STALLED, e REGISTRA as pendências

🔍 INVESTIGADOR      lê o código, o acervo e o histórico ANTES de qualquer edição
                     🔴 não escreve. Entrega o mapa e os riscos

📐 DESENHISTA DA     transforma a SPEC em critério verificável e escreve os testes
   PROVA             🔴 não implementa. Quem faz a prova não faz a resposta

🔧 BUILDER           implementa. Um por unidade independente

⚙️ VERIFICADOR       build, testes, lint, tipos, migrations, regressão
   MECÂNICO          🔴 determinístico. Não opina
                     ⛔ 📊 ESSA LISTA NÃO BASTA: é exatamente a que deixou o
                        produto 1h40 no chão com tudo verde (CLAUDE.md §9.1)
                     🔴 Mexeu em `app/`, `middleware.ts`, `instrumentation.ts`,
                        `next.config.js` ou variável de ambiente:
                          npm run test:rotas-montam   +   next start
                          + UMA REQUISIÇÃO A ROTA QUE EXECUTA CÓDIGO (/api/...)
                        Arquivo estático responde 200 com o roteador morto

⚖️ JUÍZES            um por SUPERFÍCIE DE FALHA, nunca cinco genéricos
                     🔴 contexto fresco. Não recebem a narrativa do builder

🗡️ RED TEAM          missão: FAZER QUEBRAR. Só a partir de RISCO 6 com SUPERFÍCIE 3

🧩 INTEGRADOR        procura o que só aparece na junção das partes

🏁 JUIZ FINAL        contexto limpo, olha o sistema, não o diff
```

### 🔴 A regra que mais paga, e ela é barata

> **Todo subagente reporta o que vir FORA do próprio escopo.**

📊 **Três casos medidos, todos de subagentes que analisavam outra coisa:**
um subagente encarregado do gate acusou **16 slots órfãos em rotas fora das 19**
(`SPEC-084.2-EXECUTION-REPORT.md:86-89`); e nesta própria auditoria, um subagente
mandado **contar pendências** trouxe os dois casos (P-179 e P-23) que derrubaram a
conta da v1. **Custa uma frase no prompt.**

---

## 4. O JUIZ — o que ele recebe, o que ele nunca recebe, e o que ele devolve

```
RECEBE     a SPEC · o contrato de aceitação · a referência ·
           🔴 O ARTEFATO REAL — o diff, o produto rodando, o teste, o banco

NUNCA      a narrativa do builder · o esforço · a justificativa ·
RECEBE     "está funcionando" · o resumo do que foi feito
```

**A constituição do juiz:**

```
Presuma FAIL até existir evidência de PASS.
Não premie esforço. Não considere intenção. Não aceite "parece funcionar".
Cite arquivo, linha, comando, saída ou consulta em CADA conclusão.
🔴 Se estiver bom, diga que está bom. Um juiz que precisa achar defeito
   para se justificar É o defeito que este protocolo existe para matar.
```

**E ele devolve sempre esta forma:**

```
VEREDITO:       PASS / FAIL
BLOCKERS:       cada um com o TESTE DO PRODUTO respondido
PENDÊNCIAS:     o que reprovou o teste do produto
EVIDÊNCIA:      o comando e a saída
MAIOR LACUNA:   uma só
PRÓXIMA AÇÃO:   uma só
CONFIANÇA:      e o que ficou por medir
```

### 🔴 Quem classifica e quem registra — e o que acontece quando discordam

```
⚖️ O JUIZ CLASSIFICA       cada achado dele sai com BLOCKER ou PENDÊNCIA,
                           e com o teste do produto respondido

🎯 O ORQUESTRADOR REGISTRA  ele escreve em PENDENCIAS.md, e é dele a decisão final

🔴 SE ELE REBAIXAR UM BLOCKER, A DISCORDÂNCIA VAI ESCRITA NO RELATÓRIO —
   o texto do juiz, o motivo do orquestrador, e o teste do produto pelos dois.
   Rebaixamento silencioso é o afrouxamento da régua que a §6 proíbe.

🔴 E NÃO SE REBAIXA: segurança, isolamento entre corretoras, ou qualquer
   achado que o CLAUDE.md §10 classifique como P0/P1. Esses só o Founder move.
```

### 🔴 PRESCRIÇÃO DE JUIZ NÃO É MEDIÇÃO

📊 Numa série de rodadas deste projeto, **cinco prescrições de juiz foram
derrubadas pela consulta seguinte** — um limiar inventado, uma margem sem origem,
um método de amostragem que inflava o teto, e duas vezes um padrão testado numa
ferramenta e aplicado em outra.

```
🔴 O juiz entrega a MEDIÇÃO junto com o achado.
🔴 O executor REPRODUZ antes de aplicar — e devolve com o número se não bater.
🔴 O juiz roda o padrão na ferramenta que vai usá-lo.
```

⚠️ **O executor não pode desqualificar um achado dizendo que é "prescrição sem
medição" — ele tem de tentar reproduzir e mostrar o resultado.** A regra corta os
dois lados.

---

## 5. 🔴 A REFERÊNCIA — o que substitui "faça excelente"

**"Qualidade máxima" não é instrução: o juiz não tem contra o que comparar.** Uma
referência resolve isso: o crítico olha dois artefatos e diz qual está melhor.

### As quatro regras

```
1. 🔴 INSPECIONÁVEL
   O juiz consegue ABRIR, RODAR ou MEDIR. Se ele só consegue imaginar,
   não é referência — é adjetivo.

2. 🔴 UM PONTO ESPECÍFICO, nunca o produto inteiro
   ❌ "faça igual ao Slack"
   ✅ "o indicador de quem está digitando do Slack: aparece em <300ms,
       some em 5s de silêncio, e nunca ocupa espaço que empurre a lista"

3. 🔴 A INTERNA VENCE A EXTERNA quando existe
   O melhor módulo do próprio repositório é melhor referência que um produto
   de fora — ele já respeita as convenções, as bibliotecas e o estilo.

   ⚠️ 📊 MAS O OUTLIER NÃO SERVE DE MODELO. A SPEC-084 mediu e registrou:
   "a Allianz é o outlier extremo" — 1.244 nós no Atlas contra a média das
   outras. Copiar o corredor mais rico produz um alvo que as outras rotas
   não alcançam, e um juiz que reprova todas elas.
   🔴 A referência interna é a MEDIANA do que já passou no gate, nunca o topo.

4. 🔴 UMA REFERÊNCIA POR DIMENSÃO, não uma para tudo
   segurança → OWASP ASVS      ·  arquitetura → o ADR aprovado
   API → o contrato OpenAPI    ·  banco → as invariantes
   UI → a tela aprovada        ·  agente → as conversas-ouro
   performance → o SLO         ·  resiliência → o cenário de falha
```

### Quem traz a referência, quando, e o que fazer se ninguém responder

```
🤖 O AGENTE PROPÕE     ele conhece o código e sabe qual módulo é o melhor
                       🔴 QUANDO: junto com a conta da §2, ANTES de montar time —
                          a referência é insumo do juiz, não conclusão do builder

🧑 O FOUNDER CONFIRMA   ele conhece o mercado e o que o corretor espera

🔴 E SE ELE NÃO RESPONDER, NÃO SE TRAVA. O CLAUDE.md §9 proíbe esperar
   aprovação entre blocos. O agente SEGUE com a referência que propôs,
   ESCRITA no relatório como "referência proposta, não confirmada" —
   e o juiz julga contra ela. Se o Founder discordar depois, o alvo muda
   e a rodada se repete contra o alvo novo.

🔴 ONDE FICA ESCRITA: na §0.1 do relatório de execução, ao lado das duas contas.
   Referência que não está escrita não existe para o juiz.

🔴 Se o agente não achar referência inspecionável para uma dimensão,
   ele DIZ ISSO em vez de inventar — e a dimensão vira "não avaliada",
   não "aprovada".
```

⚠️ **E há uma armadilha medida:** uma referência **observada** registra o que foi
feito, **não o que se deve fazer**. 📊 Num caso real, os humanos responderam *"sim"*
a *"continuar com o CPF da conversa anterior?"* — e copiar a maioria abriria o
chamado **no CPF do cliente errado**. **Referência observada precisa de julgamento
humano em toda tela de identidade, dinheiro ou escolha-entre-existente-e-novo.**

---

## 6. O LAÇO — e as três portas de saída

🔴 **Este laço é o único do canon.** Ele **substitui o laço de QUALQUER SPEC** — nomeadamente `SPEC-084 §6.3` e `SPEC-084.1 §7.2`, ambas revogadas no próprio arquivo delas — e revoga a cláusula *"reprovação sem motivo acionável não conta como volta"*, que tornava o teto inalcançável porque quem decidia se o motivo era acionável era o próprio juiz que reprovava.

⚠️ 📊 **E a forma de verificar isto é um comando, não uma leitura** — porque a v2 revogou só numa das duas e ninguém percebeu até o juiz rodar:

```bash
grep -rn "não conta como volta" docs/    # só pode sobrar dentro de bloco ⛔ REVOGADO
```

```
① o builder entrega
② o verificador mecânico roda   →  FAIL aqui não vai a juiz, volta direto
③ o juiz julga o ARTEFATO, e entrega a medição
④ 🔴 cada achado passa pelo TESTE DO PRODUTO (§1)
      blocker  → conserta
      pendência → PENDENCIAS.md, e SEGUE
⑤ julga de novo:
      🔴 VOLTA 2 — O MESMO JUIZ. Ele sabe o que cobrou.
      🔴 VOLTA 3 — UM JUIZ NOVO, contexto limpo, que NÃO vê as voltas
         anteriores. Se ele reprovar por outra coisa, o defeito é do produto;
         se reprovar pelo mesmo, o primeiro juiz estava certo; se liberar,
         o primeiro estava ancorado na própria reprovação.

🔴 TODA VOLTA CONTA. Sem exceção, e sem juiz decidindo se a própria
   reprovação foi boa o bastante para contar.
```

### As três portas

```
   ✅ o juiz libera
   📋 sobraram só pendências  →  registra e entrega
   🛑 3 voltas sem o PRODUTO mudar  →  STALLED
```

🔴 **STALLED não é uma parada — é uma CLASSIFICAÇÃO obrigatória.** O `CLAUDE.md`
§10 lista as oito únicas condições de parada, e o protocolo não cria uma nona:

```
3 voltas sem o produto mudar → o orquestrador CLASSIFICA:

   isto é uma das OITO condições do CLAUDE.md §10?

   SIM  →  para, registra o dossiê, e é a §10 que autoriza a parada.
           Escopo → FOUNDER-DECISIONS.md · técnica → PENDENCIAS.md

   NÃO  →  🔴 NÃO PARA. Entrega o que passou, registra o resto em
           PENDENCIAS.md com o dossiê, e AVANÇA.
           CLAUDE.md §10 é literal: "fora disso, complete o bloco,
           execute o VERIFY e avance."
```

**A porta ③ existe para forçar a classificação, não para autorizar a trava.**

```
🔴 NUNCA: afrouxar a régua, alterar o teste para passar, ou declarar pronto
   por cansaço. Nenhuma das três é uma porta.
```

---

## 7. OS MODOS — a mesma regra, cinco formas

**Não existem cinco protocolos. Existe um, e o orquestrador escolhe a forma.**

| modo | a conta da §2 governa? | o que o dimensiona |
|---|---|---|
| 🧭 INVESTIGAÇÃO · *ideia, auditoria, mapeamento, medição* | ❌ não (§2.5) | elenco de 4, × largura |
| 📝 SPEC | ✅ sim | RISCO e SUPERFÍCIE **do que a SPEC vai mandar fazer** |
| 🔨 EXECUÇÃO | ✅ sim, por unidade de trabalho | as duas contas |
| 🤖 AGENTE | ✅ sim, e com três travas próprias | as duas contas |
| 🚨 INCIDENTE | ❌ não | elenco mínimo, e o juiz vem depois |

### 🧭 MODO INVESTIGAÇÃO — *ideia nova, auditoria, mapeamento, "isto funcionou?"*

**A saída não é código. É uma recomendação com evidência.** 🔴 **Um elenco de quatro,
REPLICADO por frente independente** — a largura é o que dimensiona.

```
INVESTIGADOR    o que é, quem já usa, e desde quando funciona
                🔴 e o que MUDOU nos últimos 3 meses — o campo se move rápido
                ⚠️  em AUDITORIA ele é quem MEDE o estado, e todo número sai
                   com a consulta que o produziu
ANALISTA        onde encaixa no AutoBrokers: qual peça existente ela substitui,
                melhora ou duplica
                🔴 CLAUDE.md §5: consolidar antes de duplicar
CÉTICO          por que NÃO fazer: custo, dependência nova, o que quebra,
                o que ninguém está medindo
JUIZ DO VALOR   quantos atendimentos por mês isso melhora, e em quanto

SAÍDA:  FAZER AGORA · FAZER DEPOIS (com o que destrava) · NÃO FAZER (com o porquê)
        🔴 e "não fazer" é um resultado legítimo. O protocolo não existe
           para aprovar ideias.
        🔴 "FAZER" sai com as duas contas da §2 já feitas — é o que ele entrega
           para quem vai executar.
```

### 📝 MODO SPEC — *escrever o documento que outro vai executar*

```
INVESTIGADOR    mede o estado atual. 🔴 Todo número da SPEC nasce de uma consulta
DESENHISTA      escreve os gates ANTES do texto — se não dá para verificar,
                não entra
BUILDER         escreve a SPEC
JUIZ            🔴 a pergunta dele é uma: "um chat novo, lendo só isto,
                executa sem perguntar nada?"
                E ele TENTA — abre os arquivos que a SPEC cita e confere
                que existem
```

🔴 **A SPEC pontua o TRABALHO QUE ELA MANDA FAZER, não o ato de escrevê-la.** Uma
SPEC que manda tocar o disparo às seguradoras é RISCO 8 mesmo sendo um `.md`. **E
o time da §2 é o time da execução, montado pela própria SPEC** — o modo SPEC
encadeia no modo EXECUÇÃO, e a conta atravessa os dois.

🔴 **O defeito característico deste modo, e ele apareceu em seis versões seguidas:**
a correção entra no corpo e **não sobe para o gate, para o relatório, nem para o
resumo**. **Depois de cada reescrita, `grep` por cada conceito que mudou de
definição — releitura nunca achou nenhum deles.** 📊 Cinco casos na SPEC-084.1
(`:296`, `:182`, `:472`, `:282`, `:1196`) e um sexto na execução que gerou este
protocolo: o achado da 3ª volta nunca subiu para o relatório —
`grep -c "P-084-83" SPEC-084.2-EXECUTION-REPORT.md` → **0**.

### 🔨 MODO EXECUÇÃO — *fazer o que a SPEC manda*

```
Time pelas duas contas da §2, por unidade de trabalho.
🔴 Um worktree por builder quando dois tocam o mesmo arquivo.
🔴 A integração é SERIAL, e a regressão roda depois de CADA merge.
📊 Motivo medido: dois agentes na mesma árvore reverteram consertos um do
   outro em silêncio, e os testes passaram medindo uma verdade antiga.
```

### 🤖 MODO AGENTE — *a Central de Agentes, auto-evolução, destilação*

**Este é o modo mais perigoso, porque roda sem ninguém olhando.**

```
🔴 TRÊS TRAVAS OBRIGATÓRIAS, e nenhuma é negociável:

1. TETO DE VOLTAS DURO, contado e registrado.
   Bateu → para e avisa. Nunca "mais uma tentativa".

2. TETO DE CUSTO por execução, declarado antes de começar.
   🔴 Um laço de qualidade sem teto de custo é uma fatura sem limite.

3. O QUE ELE MUDA É REVERSÍVEL E FICA REGISTRADO.
   Auto-evolução que sobrescreve sem histórico não é evolução: é perda.

E o critério de parada é o mesmo TESTE DO PRODUTO — um agente que
"melhorou" algo que não muda o atendimento gastou dinheiro à toa.
```

### 🚨 MODO INCIDENTE — *o produto está no chão, e a lentidão É o dano*

📊 **Este modo existe porque o buraco foi medido três vezes:** 1h40 de produto
fora do ar com todos os gates verdes (`CLAUDE.md §9.1`); a captura parada **3
dias** com o painel dizendo *"Conectado"*; e *"a Resulta não observa WhatsApp há
**15 dias**"*.

```
🔴 A CONTA DA §2 NÃO SE APLICA. Ela pontuaria RISCO 8 + SUPERFÍCIE 3 e
   convocaria red team com o produto no chão. Durante a queda, nada chega
   a ninguém — o custo de ser lento é o dano.

ELENCO MÍNIMO, e ninguém mais:
   🔧 quem conserta
   👁️ quem observa o EFEITO — o produto voltou? uma rota que EXECUTA
      CÓDIGO responde? (CLAUDE.md §9.1: nunca um arquivo estático)

🔴 O CONSERTO DE INCIDENTE É REVERSÍVEL POR CONSTRUÇÃO:
   feature flag, revert, ou desligar. Se o conserto mais rápido é
   irreversível, ele NÃO é o conserto — é a segunda queda.

🔴 O JUIZ NÃO É DISPENSADO, É ADIADO. Ele vem no post-mortem, com contexto
   fresco, e julga DUAS coisas: o conserto e a CAUSA.
   O conserto definitivo volta para a conta da §2, normalmente.

🔴 E o incidente é a condição (1) ou (4) do CLAUDE.md §10 quando houver
   risco de perda de dado ou vazamento — aí para tudo e avisa o Founder.
```

---

## 8. O QUE ISTO NÃO É, E QUANDO NÃO SE APLICA

```
❌ não se aplica quando a tabela da §2.3 diz "ninguém" — RISCO 0–1 com
   SUPERFÍCIE 0. Trocar uma palavra num comentário é trocar uma palavra
❌ não se aplica a rodar um comando de leitura, ler um arquivo, ou responder
   uma CONSULTA PONTUAL — "onde está X?", "o que essa função faz?"
   ⚠️ varredura que vira conclusão NÃO é consulta pontual: é MODO
      INVESTIGAÇÃO. A fronteira entre as duas está escrita na §2.5
❌ não substitui o CLAUDE.md: as regras invioláveis vencem este protocolo,
   e a §6 mostra como o STALLED se acomoda ao §10 em vez de contrariá-lo
❌ não substitui a SPEC: ela diz O QUE, este diz COMO
❌ não é para ser lido inteiro toda vez. §1, §2 e §6 resolvem 90% dos casos
```

🔴 **E a exceção que o Founder pode invocar a qualquer momento:** *"isto é mais
importante do que parece"* — e o RISCO sobe para 6. Ele conhece o negócio; a conta
não. ⚠️ **Não existe a exceção contrária:** ninguém baixa o RISCO por pressa. Quem
tem pressa usa o MODO INCIDENTE, que é declarado e fica escrito.

---

## 9. QUEM DECIDE USAR

**O orquestrador, sozinho, sempre.** Ele faz as duas contas da §2 e monta o time.

🔴 **O Founder nunca precisa pedir.** Se precisar, o protocolo falhou.

---

## 10. DE ONDE VIERAM ESTAS REGRAS

**O que veio de fora, e é consenso da fronteira em 2026:**
- builder ≠ juiz, e o juiz com contexto fresco · **Anthropic**, harness de
  aplicações longas (Planner/Generator/Evaluator)
- o contrato de aceitação antes do código · **Anthropic**, o *Sprint Contract*
- o juiz vendo o artefato real, não o resumo · **OpenAI**, harness engineering
- a referência externa concreta em vez de "faça bom" · **Shumer**, Gauntlet Loop
- hard gates antes de nota, e um juiz por superfície · **Anthropic**, evals
- risco e tamanho como eixos separados · prática padrão de *change management*
  (a matriz risco × esforço), aqui adaptada a agentes

**O que é calibração deste projeto, medida aqui — e pode não generalizar:**
- o teste do produto como regra de parada
- os quatro números, e os cortes em 2/6 (RISCO) e 0/1–2/3 (SUPERFÍCIE)
- o teto de 3 voltas, e o juiz novo na terceira
- *"todo subagente reporta fora do escopo"*
- *"grep por conceito, nunca releitura"*
- o MODO INCIDENTE com juiz adiado

⚠️ **Os números desta segunda lista são de UM projeto.** Quando um deles errar duas
vezes seguidas, **muda o número e registra por quê** — este arquivo é versionado
para isso.

---

## 11. O QUE MUDOU DA v1 PARA A v2, E POR QUÊ

📊 **A v1 foi submetida ao próprio protocolo e reprovou com sete blockers.** O
laço não travou julgando a si mesmo — a §1 funcionou e rebaixou seis achados do
juiz a pendência. O que falhou foi a §2, que era a parte inventada e não medida.

| # | o defeito da v1 | o conserto |
|---|---|---|
| B1 | o arquivo não estava commitado nem no `CLAUDE.md` — nenhum agente o abriria | commitado, e no bootstrap §2 e na ordem de autoridade §3 do `CLAUDE.md` |
| B2 | a conta dava **três respostas** para uma palavra numa mensagem, **9 agentes** para um `COMMENT` e **zero** para 117 commits em produção | §2 refeita: RISCO × SUPERFÍCIE, piso por EFEITO, e os seis casos re-pontuados em §2.6 |
| B3 | a conta não governava 3 dos 4 modos, e dava 0 para toda avaliação de ideia | §2.5: a conta vale para mudança, não para investigação; tabela dos modos em §7 |
| B4 | §3 e §4 discordavam sobre quem declara pendência — a única alavanca que para o laço | §4: o juiz **classifica**, o orquestrador **registra**, e o rebaixamento vai **escrito** |
| B5 | STALLED não é nenhuma das oito condições de parada do `CLAUDE.md` §10 — nascia morta | §6: STALLED é **classificação**, não parada. Ou cai numa das oito, ou entrega e avança |
| B6 | o laço era cópia do que já falhara, e não revogava *"reprovação inacionável não conta como volta"* | §6 declara precedência, revoga a cláusula, e **toda volta conta** |
| B7 | não havia modo para incidente, e a conta **atrasava** a volta do produto | §7: MODO INCIDENTE, elenco mínimo, conserto reversível, juiz adiado |

### A VOLTA 2 — mais cinco, e dois deles o conserto da v1 abriu

📊 **A prova de que a §2 funciona veio primeiro:** o juiz novo aplicou as §2.1–§2.5
aos seis casos **antes** de abrir a §2.6, e chegou ao **mesmo time nos seis**. Isso não
é palpite — é reprodução por um segundo leitor.

| # | o defeito da v2 | o conserto |
|---|---|---|
| 1 | 🔴 a isenção de `GRANT` e `índice` da §2.4 dava **"ninguém"** à única migration de vazamento entre corretoras do repositório, e ao índice que **é** a fronteira estrutural | só o `COMMENT` fica isento; o piso passa a dizer **"altera dado, estrutura, TRAVA ou QUEM PODE LER"** |
| 2 | **o B6 não fechou**: a cláusula estava viva também em `SPEC-084 §6.3`, e eu não rodei o `grep` que a §7 manda rodar | revogada nas duas, o §6 nomeia **qualquer SPEC**, e traz o comando de verificação escrito |
| 3 | a trava *"não sei onde isto pega"* dava SUPERFÍCIE **3** a qualquer linha de prompt — **nove papéis para duas linhas**, em 13% dos commits do mês | §2.2: **dois "não saber"**. Não saber onde pega é superfície; não saber se o modelo obedece é **prova** |
| 4 | o VERIFICADOR MECÂNICO da §3 listava exatamente os gates que deixaram o produto **1h40 no chão** com tudo verde | §3 passa a exigir `test:rotas-montam` + `next start` + **uma requisição a rota que executa código** |
| 5 | §2.5 e §8 davam respostas opostas à mesma frase — *"três respostas"* de novo, na seção escrita para curar isso | a fronteira **CONSULTA PONTUAL × VARREDURA**, escrita uma vez e citada nos dois lugares. MODO IDEIA vira **MODO INVESTIGAÇÃO** |

🔴 **E o defeito nº 2 é o mais instrutivo do documento inteiro:** a §7 manda *"depois de
cada reescrita, `grep` por cada conceito que mudou de definição — releitura nunca achou
nenhum deles"*. **Eu escrevi a regra e não a rodei.** O juiz rodou, e achou. A regra
pegou o autor dela — que é o único teste que vale.

**As pendências que o juiz achou e que reprovaram o teste do produto** — evidência
que não reproduzia na §1, a alegação inflada sobre a primeira volta, a referência
`allianz` que a SPEC-084 já rejeitara como outlier, e a §5 sem "quando" nem "onde"
— **foram consertadas junto**, porque o custo era uma linha cada.

⚠️ **O que continua por medir:** 💭 **nenhum orquestrador rodou sob este protocolo
ainda.** Tudo aqui é análise de documento contra repositório. **A prova é a
primeira SPEC executada sob ele** — e o número a vigiar é se a §2 continua
separando os casos quando eles não forem os seis que a calibraram.
