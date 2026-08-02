---
> **Status:** canônica · é o portão final antes do uso real
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Autoridade superior:** CLAUDE.md · SPEC-054 (segurança) · SPEC-062 (evals,
> billing, go-live)
> **Origem:** CA-020 · pendências do relatório da SPEC-062 · pedido do Founder de
> auditoria externa com outros modelos
> **Branch:** `feat/spec068-prontidao-go-live`
---

# SPEC-068 — Prontidão e Go-Live

> **A frase que resume:** hoje, todo endereço sob `/api/` passa pelo middleware
> **sem nenhuma checagem de sessão**. As rotas conferem por conta própria — e é
> aí que mora o risco: **a proteção depende de cada autor lembrar.** Uma rota
> nova mal escrita **nasce pública**, e ninguém recebe sinal disso.

---

## 1. Por que esta SPEC existe

**É o portão, não a festa.** Tudo que as SPECs 063 a 067 constroem só chega ao
cliente por aqui.

### 1.1 O que ela entrega

```
nenhuma rota nasce pública por esquecimento
toda mudança de qualidade é medida, não sentida
outros modelos leram tudo e disseram o que não vimos
o canário roda com número conferido à mão
e existe um botão de desligar, escrito, para quando algo der errado
```

### 1.2 O que ela NÃO faz

| Fora do escopo | Onde vai |
|---|---|
| construir funcionalidade nova | 063 a 067 |
| preço, plano, invoice | SPEC-062 · CLAUDE.md §13.6 |
| canais definitivos (Meta, SES) | SPEC-069 |

---

# BLOCO 0 — A auditoria, que aqui é dupla

**Obrigatório, e com duas partes.**

## 0.1 A auditoria interna

O padrão das outras SPECs: cada afirmação ainda é verdade · o que mudou · o que
não foi previsto · o que pode ser melhor · o que vai quebrar.

**Mais uma pergunta específica desta SPEC:**

```
[ ] as SPECs 063 a 067 foram executadas e seus gates fecharam?
[ ] existe alguma pendência delas que impede o go-live?
```

## 0.2 A auditoria externa — o Bloco C, executado antes

**O Bloco C desta SPEC roda dentro do Bloco 0**, não depois. A razão: se outro
modelo achar um problema estrutural, é melhor saber **antes** de mexer no
middleware, não depois.

## 0.3 O relatório

**✅ confirmado · ⚠️ corrigido · ➕ acrescentado · ❓ em aberto · 🚫 retirado**,
mais:

```
🔍 ACHADOS EXTERNOS ..... o que outro modelo viu e nós não
```

---

# BLOCO A — CA-020: o middleware que libera tudo

**Grau: P1.** Registrado em `CHANGE-ADDENDA.md` como **ESSENCIAL**, autorizado
pelo Founder para esta SPEC.

## A.1 O defeito

```ts
const isApiRoute = apiRoutes.includes(pathname) || pathname.startsWith('/api/');
if (isPublicRoute || isPublicPrefix || isApiRoute) return response;
```

**Todo endereço sob `/api/` passa sem nenhuma checagem de sessão.**

## A.2 A evidência

Medido em produção em 27/07/2026, **sem cookie nenhum**:

```
GET /dashboard                              → 307 para /login
GET /admin/companies                        → 307 para /admin/login
GET /api/admin/proxy/agents/company/<id>/…  → 200 COM O PROMPT DA CORRETORA
```

`lib/admin-proxy.ts` era uma das rotas que não conferiam: **carimbava a chave de
plataforma em requisição de qualquer pessoa da internet** e entregava ao backend,
que obedecia — GET, PUT e DELETE em agente de qualquer corretora.

**Origem:** primeiro commit do repositório, 04/06/2026, do código original.

## A.3 O que já foi feito, e por que não basta

O buraco conhecido foi fechado em dois commits — só sessão de plataforma passa.

**A causa de raiz continua.** O padrão é o oposto do que deveria ser:

> **Uma rota nova mal escrita nasce pública, e o autor não recebe nenhum sinal.**

## A.4 A correção: inverter o padrão

```
ANTES ..... tudo sob /api/ passa; a rota confere se lembrar
DEPOIS .... o middleware EXIGE sessão em /api/** por omissão
            e o que é público entra numa lista CURTA e EXPLÍCITA
```

**A lista de exceções, e ela é curta:**

```
/api/auth/login
/api/admin/login
webhooks com token próprio          (verificado por hash, não por sessão)
/embed/                             (superfície pública declarada)
/api/health                         (sem dado, só estado)
```

**Nada mais.** E acrescentar item a essa lista exige comentário dizendo por quê.

## A.5 O sinal que faltava

Hoje o autor de uma rota nova não sabe que ela nasceu pública. **Passa a saber:**

```
1. a lista de exceções é um arquivo só, com comentário obrigatório por item
2. teste que enumera TODAS as rotas /api/ e prova que cada uma
   ou exige sessão, ou está na lista com justificativa
3. rota nova sem sessão e fora da lista → o teste QUEBRA
```

**É o teste que impede a regressão, não a boa intenção.**

## A.6 A migração sem quebrar

Inverter o padrão pode derrubar rota legítima que dependia do buraco.

```
1. instrumentar: registrar toda requisição a /api/ com e sem sessão
2. rodar em modo sombra por um período — nega nada, só registra
3. listar o que passaria a ser negado
4. classificar: é legítimo e precisa de exceção, ou é o buraco?
5. só então ligar
```

**Sem o passo 2, ligar às cegas quebra o produto.**

## A.7 Testes

| # | Prova |
|---|---|
| A1 | rota `/api/` sem sessão e fora da lista → 401 |
| A2 | o teste enumera todas as rotas e nenhuma escapa |
| A3 | toda exceção tem justificativa escrita |
| A4 | webhook com token próprio continua funcionando |
| A5 | rota nova sem proteção quebra o teste |
| A6 | o modo sombra registra sem negar |

---

# BLOCO B — O conjunto de perguntas com resposta certa

**Sem ele, nenhuma medida de qualidade existe.**

## B.1 O que é

```
~200 perguntas reais de corretor e de segurado
cada uma com a resposta ou a carta que DEVERIA aparecer
```

## B.2 De onde vêm

**Das 69.150 transcrições.** São perguntas que pessoas realmente fizeram — não
inventadas.

**Por que isso importa:** pergunta sintética mede o que imaginamos que perguntam.
**Pergunta real mede o que perguntam.**

**E há um alerta que a pesquisa trouxe:** gerar conteúdo sintético em domínio
especialista produz texto plausível e sutilmente errado — que só um corretor
detecta. **A estrutura pode ser sintética; o conteúdo, não.**

## B.3 A composição

```
por serviço ....... assistência · sinistro · cobrança · dúvida · renovação
por ramo .......... auto · residencial · condomínio · vida · empresarial
por dificuldade ... resposta direta · exige a apólice · exige a versão certa
                    · não tem resposta (e o certo é dizer que não tem)
```

**A quarta categoria é a mais importante e a mais esquecida:** o sistema precisa
ser medido também no que ele **não** deve responder.

## B.4 Como se usa

```
CI .................. roda a cada mudança que toca busca ou prompt
regressão ........... se cair, quebra o build
antes e depois ...... nenhuma troca de modelo entra sem as duas medidas
held-out ............ 20% nunca é usado para ajustar — só para conferir
```

## B.5 O que se mede

```
recall .............. a carta certa apareceu entre as recuperadas?
posição ............. em que lugar?
resposta ............ o agente usou a carta certa?
recusa correta ...... quando não havia resposta, ele disse que não havia?
```

## B.6 O juiz

Quando a avaliação exigir julgamento, ele segue três regras da pesquisa:

```
binário, nunca nota de 1 a 5 — "escala de 1 a 5 costuma ser sinal de
   processo de avaliação ruim"
com crítica escrita — o juiz diz POR QUÊ
modelo diferente do gerador — LLM superavalia sistematicamente a própria saída
```

**E revalidado a cada troca de modelo.** Juiz não é constante.

## B.7 Testes

| # | Prova |
|---|---|
| B1 | o conjunto tem ao menos 200 perguntas, todas de origem real |
| B2 | as quatro dificuldades estão representadas |
| B3 | 20% é held-out e nunca foi usado para ajustar |
| B4 | o juiz é modelo diferente do gerador |
| B5 | queda no conjunto quebra o build |

---

# BLOCO C — A auditoria externa

**Executada dentro do Bloco 0.**

## C.1 Por que ela existe

> **Somos os piores auditores do que escrevemos.**

Seis auditorias internas nesta sessão mudaram o plano seis vezes — e todas foram
feitas por mim, sobre o que eu mesmo tinha escrito. **Outro modelo, sem apego,
vê o que a gente naturaliza.**

## C.2 O que cada auditor recebe

```
as SPECs 063 a 068, inteiras
acesso de LEITURA ao código
acesso de LEITURA ao banco
o histórico das decisões (FOUNDER-DECISIONS.md, CHANGE-ADDENDA.md)
```

**E uma instrução dura:** *procure o que está errado, não o que está bom.*

## C.3 As perguntas que cada um responde

```
1. o que está errado nas SPECs que ninguém viu?
2. o que elas prometem e o código não consegue entregar?
3. que risco de segurança ou de vazamento passou?
4. o que é mais complicado do que precisa ser?
5. o que está faltando e é óbvio para quem chega de fora?
6. se você tivesse que apostar contra este plano, onde apostaria?
```

**A sexta é a que mais rende.**

## C.4 Os auditores

```
um modelo de outra família     (GPT Sol ou equivalente)
um modelo do topo              (Fable ou equivalente)
e, se possível, um terceiro
```

**Nunca só um.** Dois modelos que discordam ensinam mais que um que concorda.

**Decisão do Founder:** quais modelos, e se eles leem as SPECs, o código, ou os
dois.

## C.5 O que se faz com o resultado

```
cada achado é classificado:  procede · não procede · precisa investigar
os que procedem viram item de correção ANTES do go-live
os que não procedem ficam registrados com o motivo
   (para o próximo auditor não repetir)
```

## C.6 Testes

| # | Prova |
|---|---|
| C1 | ao menos dois modelos de famílias diferentes auditaram |
| C2 | todo achado foi classificado, nenhum ficou sem resposta |
| C3 | achado que procede virou item de correção |

---

# BLOCO D — As pendências da SPEC-062

## D.1 Prova de restore

**Backup que nunca foi restaurado não é backup.**

```
[ ] restaurar o backup mais recente num ambiente separado
[ ] provar que o dado está lá e íntegro
[ ] medir quanto tempo levou
[ ] registrar o resultado com data
```

## D.2 RPO e RTO, declarados

```
RPO ..... quanto dado podemos perder, no pior caso
RTO ..... quanto tempo levamos para voltar
```

**Hoje não estão escritos em lugar nenhum.** Sem eles, ninguém sabe se o que
existe é suficiente — nem nós, nem o cliente.

## D.3 OpenTelemetry

Instrumentar com as convenções `gen_ai.*` — **não com SDK de fornecedor.**

```
por quê ..... torna o backend de observabilidade trocável
o que ....... invoke_agent · execute_tool · invoke_workflow · plan
              tokens de entrada e saída · custo · latência
por tenant .. sempre. Custo sem tenant não serve para nada.
```

**A escolha do backend (Langfuse self-hosted é o candidato) é da SPEC-069.**
Aqui é só a instrumentação, que não depende dela.

## D.4 O Bloco B de billing

**Travado por decisão do Founder.** Fica registrado como pendente, com o que
falta e o que depende da decisão. **Não é executado aqui.**

⚠️ **E um risco que a auditoria encontrou:** existe uma tarefa agendada a cada 5
minutos que busca uso não faturado — hoje ~1.239 linhas. **O que separa as
corretoras de um débito retroativo é uma variável de ambiente ausente.**

```
[ ] confirmar que a trava está ativa
[ ] e que ela é positiva (exige ligar), não negativa (exige desligar)
```

## D.5 Testes

| # | Prova |
|---|---|
| D1 | o restore foi executado e o resultado registrado com data |
| D2 | RPO e RTO estão escritos e são verificáveis |
| D3 | os spans `gen_ai.*` saem com tenant |
| D4 | a trava de billing é fail-closed |

---

# BLOCO E — O canário

## E.1 A regra que sustenta tudo

> **Nada é apresentado como certo sem alguém ter olhado.**

## E.2 A ordem

```
1. o Founder, no número dele
   → tudo. Atendimento, cobrança, achado, entrega.

2. Resulta, com uma coisa só ligada
   → a mais simples. Uma semana.

3. Resulta, com o resto
   → uma semana.

4. AutoFleet
   → só depois de a Resulta rodar duas semanas sem incidente.
```

**Nunca as duas ao mesmo tempo.** Se algo der errado, precisamos saber em qual.

## E.3 O que se confere à mão

**Antes de qualquer mensagem sair para segurado ou corretor:**

```
o primeiro achado de cada análise      → o número bate?
a primeira cobrança                    → o boleto é o certo, o valor é o certo?
o primeiro handoff                     → chegou em quem devia?
a primeira resposta sobre cobertura    → citou a versão certa?
o primeiro acionamento                 → em modo teste, cancelou antes?
```

**Cada um conferido por gente, uma vez.** Depois disso, amostragem.

## E.4 O que se mede durante o canário

```
diário .... quantas mensagens saíram, para quem, por qual número
            quantos achados, quantos o corretor abriu
            quantos ele marcou como "não é isso"
semanal ... o corretor achou útil? (pergunta direta, uma vez por semana)
```

**A pergunta semanal é o dado mais importante do canário** — e não sai de log
nenhum.

## E.5 Os critérios de parada

**Para tudo, imediatamente, se:**

```
✗ mensagem sair para o cliente errado
✗ dado de um tenant aparecer em outro
✗ o agente afirmar cobertura sem ter consultado
✗ número de WhatsApp receber aviso de restrição
✗ achado com número errado chegar ao corretor
```

**Qualquer um desses é parada total, não investigação com o sistema rodando.**

## E.6 Testes

| # | Prova |
|---|---|
| E1 | o canário roda uma corretora por vez |
| E2 | o primeiro de cada tipo foi conferido à mão, com registro |
| E3 | os critérios de parada estão implementados como alerta automático |
| E4 | a pergunta semanal é feita e registrada |

---

# BLOCO F — O desligamento de emergência

**Hoje isso não está escrito em lugar nenhum. É a diferença entre um susto e um
incidente.**

## F.1 Os quatro níveis

```
NÍVEL 1 · uma rotina
   desliga uma rotina de um auxiliar de uma corretora
   quem pode: o corretor, no dashboard

NÍVEL 2 · um auxiliar
   desliga o auxiliar inteiro daquela corretora
   quem pode: o corretor, no dashboard

NÍVEL 3 · um canal
   para todo envio frio de uma corretora, preservando o reativo
   quem pode: admin

NÍVEL 4 · tudo
   para toda saída de todas as corretoras
   o observador continua capturando; o agente para de responder
   quem pode: admin
```

## F.2 O que cada nível preserva

**Regra:** desligar nunca perde dado.

```
o observador NUNCA para — a captura continua
a fila NUNCA é descartada — fica parada, retomável
o que já foi entregue permanece consultável
```

## F.3 O tempo

```
nível 1 e 2 ..... efeito imediato, no próximo ciclo
nível 3 e 4 ..... efeito em segundos, e interrompe o que está em voo
                  (o que já saiu, saiu — não há como voltar)
```

## F.4 O religamento

**Nunca automático.** Quem desligou, ou um admin, religa — **e o sistema pergunta
o que foi resolvido**, registrando a resposta.

```
"O envio da Resulta está parado desde ontem 14h.
 O que foi resolvido?"
```

**Isso vira histórico de incidente sem ninguém precisar abrir um documento.**

## F.5 O ensaio

**O desligamento é ensaiado antes do go-live, com o Founder assistindo.**

```
[ ] desligar nível 4, cronometrar
[ ] confirmar que o observador continua capturando
[ ] religar e confirmar que a fila retomou sem duplicar
```

**Botão de emergência que nunca foi testado não é botão de emergência.**

## F.6 Testes

| # | Prova |
|---|---|
| F1 | cada nível desliga o que deve e preserva o resto |
| F2 | o observador continua capturando em todos os níveis |
| F3 | a fila não é descartada |
| F4 | religar retoma sem duplicar |
| F5 | o religamento pede e registra o motivo |
| F6 | o ensaio foi executado e cronometrado |

---

# 2. Gate final da SPEC — e do projeto

```
[ ] o relatório do Bloco 0, com os achados externos classificados
[ ] os 6 testes do Bloco A     [ ] os 4 testes do Bloco D
[ ] os 5 testes do Bloco B     [ ] os 4 testes do Bloco E
[ ] os 3 testes do Bloco C     [ ] os 6 testes do Bloco F
[ ] a suíte inteira verde
[ ] os gates das SPECs 063 a 067 fechados
[ ] o ensaio de desligamento executado
[ ] o canário do Founder rodou sem incidente
```

## 2.1 A prova viva final

```
1. rota nova sem proteção          → o teste quebra
2. o conjunto de perguntas         → passa, e a medida está registrada
3. dois modelos externos           → auditaram, e os achados foram tratados
4. restore                         → executado, com tempo medido
5. desligamento nível 4            → cronometrado, e o observador continuou
6. uma semana no número do Founder → sem nenhum critério de parada acionado
```

---

# 3. Riscos

| Risco | Mitigação |
|---|---|
| inverter o middleware quebrar rota legítima | modo sombra antes de ligar |
| o conjunto de perguntas medir o que não importa | perguntas de origem real, com held-out |
| auditoria externa virar lista de opinião | cada achado classificado, com motivo do descarte |
| canário nas duas corretoras ao mesmo tempo | uma por vez, com duas semanas de intervalo |
| desligamento nunca testado falhar na hora | ensaio obrigatório antes do go-live |
| débito retroativo de billing | trava fail-closed, verificada |

---

# 4. O que NÃO pode acontecer

```
✗ go-live com gate de qualquer SPEC anterior aberto
✗ rota /api/ nova sem sessão e sem justificativa escrita
✗ troca de modelo sem medida antes e depois
✗ canário nas duas corretoras ao mesmo tempo
✗ mensagem para cliente real sem o primeiro caso conferido à mão
✗ desligamento de emergência sem ensaio
✗ inventar preço, plano ou cobrança (CLAUDE.md §13.6)
```
