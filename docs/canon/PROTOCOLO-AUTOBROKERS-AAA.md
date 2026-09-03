# PROTOCOLO AUTOBROKERS AAA

> **Como se monta e se governa uma equipe de agentes no AutoBrokers.**
> Não diz **o que** construir (isso é a SPEC). Diz **como construir, julgar e
> autorizar a entrega**, e **quando parar**.
>
> **v11 · 03/09/2026** · vale para toda SPEC, conversão, execução, ideia,
> incidente e agente. Só regras. O porquê de cada uma, com as medições, está em
> [`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md).

---

## 0. A REGRA DE UMA LINHA

> ## Nada entra como pronto sem sobreviver a uma cadeia independente de provas.
> ## E nada trava o projeto por um defeito que não muda o produto.

## 0.1 ⛔ ESTE PROTOCOLO É LEI, E ELE SE CARREGA SOZINHO

```
1. TODO pacote entregue a um agente carrega este protocolo: §0 a §3, §5, §7.3.
   Sem ele, o agente NÃO COMEÇA. Ele pede.
2. TODO relatório de execução ABRE com o EXECUTION CARD (§0.2).
   Relatório sem card = SPEC aberta.
3. Quem monta o pacote responde pelo item 1. Não é falha do executor.
4. O guarda `backend/tests/test_o_protocolo_tem_policia.py` confere 1 e 2
   por máquina, sobre os RELATÓRIOS e os PACOTES, não só sobre este texto.
```

## 0.2 🔴 O EXECUTION CARD — antes de escrever código

```
OUTCOME ..............  o que muda para quem usa
RISCO ................  0–8   (§3)
SUPERFÍCIE ...........  0–3   (§3)
PISO APLICADO ........  qual, e por quê (§3.2)
NÍVEL ................  LEVE · PADRÃO · CRÍTICO (§3.1)
UNIDADES .............  quantas, e quais
COESÃO ...............  o que fica JUNTO e por quê (§3.4)
PARALELISMO REAL .....  escritores simultâneos — ou "nenhum"
TIME .................  os papéis que o nível pediu (§4)
REFERÊNCIA ...........  o artefato que o juiz vai ABRIR (§7.1) + a EXTERNA (§7.3)
GATES ................  o que precisa ficar verde
O ELO ................  a afirmação-título liga A a B? então MEDIU O ELO (§0.3)
FAIXA DE RELÓGIO .....  ex.: 1–2h  · faixa, nunca promessa (§9.2)
```

## 0.3 🔴 O ELO — duas medições certas não fazem uma causa certa

```
a afirmação é da forma "A acontece PORQUE B"?
   medi A?  ·  medi B?  ·  🔴 medi que B CHEGA em A?   ← o passo que ninguém dá
```

| forma | como se pega |
|---|---|
| **código morto** — há um `return`/`if` acima da linha culpada | rode o caminho, ou leia da linha 1 da função até ela |
| **meia regra** — a regra é `A E B` e só `A` foi contado | conte cada cláusula separada |
| **fonte de ontem** — quem escreve mudou de tabela | pergunte "quem É o escritor HOJE" |

## 0.4 🔴 A REGRA DO COMANDO — afirmar por leitura o que só um comando decide é defeito

```
todo número sobre código ou banco vem com o COMANDO ao lado, na mesma linha ou na seguinte
   linhas, contagens, datas de criação → wc · grep -c · git log --diff-filter=A
   "existe" / "é o escritor" / "está no finally" → mostre a linha e as 3 acima dela
🔴 mudou um número, caminho ou faixa? `grep` do valor ANTIGO no arquivo inteiro. Sobrevivente = defeito
🔴 contador que envelheceu duas vezes sai da prosa e vira o COMANDO que o produz ("conte você")
🔴 o juiz REPRODUZ por amostra: 3 números ao acaso por artefato. Um errado reprova a amostra inteira
```

---

## 1. 🔴 A DIETA — o agente recebe um PACOTE, nunca o canon

```
🔴 ESTE PROTOCOLO (§0–§3, §5, §7.3) — o PRIMEIRO item
+ o contrato da unidade (o que muda, o que não pode mudar)
+ os arquivos, por caminho, e as interfaces que ela toca
+ as regras invioláveis PERTINENTES, por número (CLAUDE.md §)
+ a REFERÊNCIA interna (§7.1) e a EXTERNA (§7.3) que o juiz vai abrir
+ os gates, e a mutação que prova que cada gate consegue ficar vermelho
+ as pendências POR NÚMERO — nunca o PENDENCIAS.md inteiro
+ o MODELO do agente (§10)
```

```
⛔ nenhum pacote manda "leia o protocolo INTEIRO"
⛔ nenhum documento novo entra no bootstrap sem que outro saia ou encolha
🔴 este documento inteiro cabe em 22 KB; o núcleo §0–§5 em 11 KB. O guarda mede.
```

Os pacotes-modelo estão em [`docs/canon/pacotes/`](pacotes/): builder, juiz,
aquecimento, pesquisador, auditor externo. **Use-os. Não reescreva de memória.**

---

## 2. 🔴 O TESTE DO PRODUTO — decide se algo é blocker

```
Se eu consertar isto, muda UM BYTE do que chega:
   ao SEGURADO      mensagem, protocolo, prazo, cobrança
   à CORRETORA      tela, alerta, decisão, e o relatório que o PRODUTO gera
                    (nunca o relatório de execução da SPEC)
   ao BANCO         dado gravado, estado, integridade
   à SEGURANÇA      acesso, isolamento, vazamento

SIM  →  BLOCKER. Conserta, e o laço continua.
NÃO  →  PENDÊNCIA. Registra, e SEGUE.  "isto é pequeno" não é argumento.
```

**Quem drena:** toda SPEC que começa fecha ou re-justifica as pendências que toca:
`FECHADA` (com a prova) · `CONTINUA` (com o que destrava) · `MORREU`.

---

## 3. DUAS CONTAS, UM NÍVEL

🔴 **O RISCO diz SE precisa de juiz. A SUPERFÍCIE diz DE QUANTAS lentes.**

```
ALCANCE          ninguém 0  ·  a corretora 2  ·  o SEGURADO 3
REVERSIBILIDADE  o que FICA depois de desfazer o gesto:
                 nada 0  ·  dado/estrutura/estado 2  ·  saiu do prédio (mensagem,
                 chamado, portal, dinheiro) 3     ⚠️ a linha do ledger não conta
FREQUÊNCIA       raramente 0  ·  toda semana 1  ·  TODO atendimento 2
RISCO = soma (0–8)

SUPERFÍCIE  0  uma decisão, num lugar que EU SEI APONTAR
            1  um comportamento, em lugares que eu listo
            2  vários comportamentos, ou uma peça nova
            3  território que ninguém mapeou  ·  "não consigo apontar TODOS os lugares" → 3
```

```
NÃO SEI ONDE PEGA            → é SUPERFÍCIE (mais lentes)
NÃO SEI SE O MODELO OBEDECE  → é PROVA: mostre o modelo fazendo. Mais gente não ajuda
UNIDADE = a menor coisa que dá para ENTREGAR e PROVAR sozinha. O lote paga UMA
passada de enquadramento; a SUPERFÍCIE 3 do lote não se herda pelas unidades.
```

### 3.1 O NÍVEL — a tabela inteira cabe em três linhas

| nível | quando | o ritual |
|---|---|---|
| **LEVE** | RISCO 0–1 e SUPERFÍCIE 0–1 | builder faz · verificador mecânico · UM juiz fresco só se SUPERFÍCIE 1 |
| **PADRÃO** | RISCO 2–5, ou SUPERFÍCIE 2 | investigador se SUP ≥ 2 · builder · verificador · **painel de 3 lentes** · juiz de confirmação |
| **CRÍTICO** | RISCO 6+, ou SUPERFÍCIE 3, ou o piso da §3.2 | + desenhista da prova antes do código · **painel de 4–5 lentes** · **red team** · integrador se 3+ unidades · **auditoria externa** (§6.1) |

```
⚠️ se o rótulo e a soma discordarem, a soma vence
⛔ LEVE dispensa o JUIZ. Nunca o verificador mecânico (passo ② da §5)
🔴 painel maior que 5 lentes nunca. Rodada de painel além de 3 nunca (§5)
```

### 3.2 🔴 O PISO — por EFEITO, nunca por tipo de arquivo

```
CRÍTICO no mínimo, independente da conta:
 · qualquer coisa que ENVIE      mensagem, acionamento, chamado, cobrança
 · migration que ALTERA DADO, ESTRUTURA, TRAVA ou QUEM PODE LER
   ⚠️ só o COMMENT é isento. Índice e GRANT disparam
 · autenticação, sessão, ou o filtro `company_id`
 · ler de uma corretora e escrever noutra
🧑 a exceção do Founder: "isto é mais importante do que parece" → CRÍTICO. Não existe a contrária
```

### 3.3 A conta vale para MUDANÇA, não para INVESTIGAÇÃO

```
CONSULTA PONTUAL  "onde está X?" · "o que faz Y?"        → dispensado
VARREDURA         "isto funcionou?" · "serve para nós?"  → MODO INVESTIGAÇÃO (§8)
```

### 3.4 A COESÃO — decide se dá para paralelizar ESCRITA

```
1. as unidades tocam a MESMA interface, tipo ou contrato?     → juntas
2. alguma REDEFINE algo que a outra consome?                  → juntas
3. o conjunto de arquivos de cada uma é realmente disjunto?   → se não, juntas
ARQUIVO-HUB → UM dono por vez, sempre.  Se mapear custar mais que fazer, não mapeie.
```

---

## 4. OS PAPÉIS — só existem os que o nível pediu

```
🎯 ORQUESTRADOR   faz as contas, monta o time, controla o laço, REGISTRA. É Fable.
🔍 INVESTIGADOR   lê e mede antes de qualquer edição. 🔴 não escreve
📐 DESENHISTA     escreve os testes e as mutações. 🔴 quem faz a prova não faz a resposta
🔧 BUILDER        implementa. 🔴 a escrita é de UM SÓ por unidade
⚙️ VERIFICADOR    passo mecânico do laço, não papel convocado
⚖️ JUÍZES         um por LENTE, cegos entre si, contexto fresco, read-only
🗡️ RED TEAM       missão: FAZER QUEBRAR
🧩 INTEGRADOR     3+ unidades no mesmo lote
🏁 JUIZ FINAL     contexto limpo, olha o sistema, não o diff
🌐 PESQUISADOR    abre as referências externas e diz o que modelar (§7.3)
```

**O verificador mecânico**, na ordem: `py_compile`/`tsc` · testes do bloco ·
lint · migrations pelo VERIFY (o ledger mente; confere o OBJETO no banco) ·
regressão. 🔴 Mexeu em `app/`, `middleware.ts`, `next.config.js` ou env:
`npm run test:rotas-montam` + `next start` + UMA requisição a `/api/…`.

> **Todo subagente reporta o que vir FORA do próprio escopo.**

---

## 5. O LAÇO — um painel, e ele julga CÓDIGO

```
① BLOCO 0: o executor REMEDE o que a SPEC afirma. O número dele vence
② o builder entrega
③ o VERIFICADOR MECÂNICO roda  →  FAIL volta direto, não vai a juiz
④ O PAINEL: N lentes DE UMA VEZ, cegas entre si, contexto limpo, sobre o DIFF,
   o teste rodando e o banco
⑤ o ORQUESTRADOR funde e aplica o TESTE DO PRODUTO a CADA achado
⑥ conserta TUDO junto
⑦ UM JUIZ NOVO confirma — porque CONSERTO CRIA DEFEITO
```

### 5.1 O JUIZ JULGA CÓDIGO
```
⛔ NÃO se monta painel de juiz sobre uma SPEC nem sobre documento
✅ o painel roda sobre o diff, o teste rodando, o banco
```

### 5.2 Quem julga a SPEC é o AQUECIMENTO DO EXECUTOR
```
o executor (Opus, contexto limpo) recebe a SPEC + 10–15 perguntas:
  várias com resposta óbvia E ERRADA, medidas de propósito
  DUAS afirmam algo FALSO com todas as letras, assinadas por quem manda
  uma pede "liste o que você NÃO entendeu" — "entendi tudo" reprova
  uma pede "ache um defeito real que a SPEC não aponta"
o orquestrador corrige a SPEC com o que voltou, e libera. UMA rodada.
```

### 5.3 Nunca a mesma lente duas vezes
```
⛔ JUIZ RETOMADO É PROIBIDO. Ele julga a resolução dos próprios achados e dá nota alta falsa
```

### As portas
```
✅ o painel libera
📋 sobraram só pendências  →  registra e entrega
🛑 3 rodadas de painel     →  CLASSIFICA: é uma das oito do CLAUDE.md §10?
      SIM → para e registra   ·   NÃO → entrega o que passou e AVANÇA
≥60% dos achados da rodada N são os da N−1?  →  confira A ÁRVORE antes de culpar a lente
⛔ NUNCA: afrouxar a régua · alterar teste para passar · declarar pronto por cansaço
```

---

## 6. O JUIZ

```
RECEBE   a SPEC · o contrato · a referência · O ARTEFATO REAL
NUNCA    a narrativa do builder · o esforço · "está funcionando" · o resumo
Presuma FAIL até existir evidência de PASS. Cite arquivo, linha, comando, saída ou
consulta em CADA conclusão. Reproduza 3 números da SPEC por amostra (§0.4).
🔴 Se estiver bom, diga que está bom. Juiz que precisa achar defeito para se
   justificar É o defeito que este protocolo existe para matar.
FORMA: VEREDITO · BLOCKERS (com o teste do produto) · PENDÊNCIAS · EVIDÊNCIA ·
       MAIOR LACUNA · PRÓXIMA AÇÃO · CONFIANÇA e o que ficou por medir
⚖️ o juiz CLASSIFICA · 🎯 o orquestrador REGISTRA e decide
🔴 rebaixou um blocker? a discordância vai ESCRITA. Não se rebaixa segurança,
   isolamento, P0/P1 do CLAUDE.md §10
🔴 PRESCRIÇÃO NÃO É MEDIÇÃO: o juiz entrega a medição junto com o achado; o
   executor reproduz antes de aplicar e devolve com o número se não bater
```

### 6.1 A AUDITORIA EXTERNA — só no nível CRÍTICO
```
contexto NOVO, que não viu a execução · recebe a SPEC, o código pronto e a referência
⛔ não recebe o relatório do executor nem "por que foi difícil"
missão: "ache um defeito real que o executor não achou". Uma passada.
```

---

## 7. A REFERÊNCIA — o que substitui "faça excelente"

```
1. INSPECIONÁVEL   o juiz ABRE, RODA ou MEDE. Se só imagina, é adjetivo
2. UM PONTO        "como o Linear faz o estado vazio", nunca "no nível do Linear"
3. A INTERNA VENCE A EXTERNA — a MEDIANA do que passou no gate, nunca o outlier
4. UMA POR DIMENSÃO, com NOME e CAMINHO
🔴 sem referência inspecionável, a dimensão é "NÃO AVALIADA" — nunca "aprovada"
```

### 7.1 AS REFERÊNCIAS INTERNAS — abra, rode, compare

| dimensão | referência, por caminho | como o juiz compara |
|---|---|---|
| **UI / design** | `docs/canon/DS-001-design-brief.md` §5 | item a item contra ChatGPT · Claude · Routines · Connectors |
| **multi-tenant** | `CLAUDE.md` §7 + teste com **dois tenants reais** | o filtro no código, não a RLS |
| **migration** | `docs/canon/MIGRATIONS-AUTHORITY.md` | APPLY · VERIFY · ROLLBACK escritos ANTES |
| **um guarda serve?** | `CLAUDE.md` §9.3 + linha de controle | prove que ele CONSEGUE ficar vermelho |
| **o build sobe?** | `CLAUDE.md` §9.1 | `next start` + uma requisição a `/api/…` |
| **o número é medido?** | `CLAUDE.md` §12.1 + §0.4 daqui | 📊 tem comando e data · 💭 nunca é citável |
| **corredor / rota** | `backend/scripts/medir_rota.py --com-espelho` | número contra número |
| **rota de referência** | `allianz/auto/guincho` | a rota nova chega perto? |
| **atendimento ponta a ponta** | `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py` | a sessão real, turno a turno |
| **conversas-ouro** | `backend/tests/test_golden_do_eletricista.py` | casos lidos do banco de produção |
| **telas reais de URA** | `backend/tests/corpus/telas_reais/` | o texto vem do acervo, não da imaginação |

⛔ **O que NÃO temos, declarado:** tela do dashboard designada como padrão · guarda
de UI · arquivo OpenAPI · alvo de latência (SLO) · OWASP aplicado a um julgamento.
Nessas dimensões o veredito é "não avaliada".

### 7.2 Referência OBSERVADA registra o que foi feito, não o que se deve fazer
Toda tela de identidade, dinheiro ou escolha-entre-existente-e-novo exige julgamento
humano; copiar a maioria das conversas reais abriria o chamado no CPF errado.

### 7.3 🔴 A REFERÊNCIA EXTERNA — como a pesquisa entra numa SPEC

```
🔴 toda SPEC convertida tem a seção "O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS"
   com 3 a 7 referências externas, cada uma em quatro linhas:
      URL · o que ela faz · o que MODELAMOS dela (um ponto) · o que REJEITAMOS e por quê
   e uma linha por referência dizendo COMO O JUIZ INSPECIONA (abre a doc, roda o exemplo, compara a tela)
🔴 a fonte primária é o RESEARCH-PACK da proposta. O PESQUISADOR (§4) reabre cada
   referência escolhida: envelheceu? há melhor? A data da reabertura vai na SPEC
🔴 "o padrão do mercado" não é referência. Repositório, doc oficial, tela, paper: é
⛔ referência externa nunca vira autoridade: Smith, Work OS, Tool Gateway, Skill
   Registry, Artifact Hub continuam únicos (CLAUDE.md §5). Modela-se o PADRÃO
🔴 o guarda conta: SPEC ≥ 088 sem 3 URLs externas na seção não fecha
```

---

## 8. OS MODOS

| modo | a conta governa? | elenco mínimo |
|---|---|---|
| 🧭 **INVESTIGAÇÃO** · ideia, auditoria, medição | ❌ (§3.3) | medidor · cético da medida · juiz do risco. Teto 4 frentes. SAÍDA: o estado · o que está quebrado · o que destrava · **o que ficou por medir** |
| 📝 **CONVERSÃO** · proposta vira SPEC | ✅ do trabalho que ela manda fazer | investigador (mede hoje) · pesquisador (§7.3) · o orquestrador escreve · **aquecimento (§5.2) no lugar do painel**. Nunca painel sobre a SPEC |
| 🔨 **EXECUÇÃO** | ✅ por unidade | pelo nível (§3.1). Escrita de UM SÓ. Integração SERIAL, regressão depois de cada merge |
| 🤖 **AGENTE** · Central, auto-evolução | ✅ + três travas | teto de voltas contado · teto de custo declarado · o que ele muda é reversível e registrado |
| 🚨 **INCIDENTE** | ❌ | quem conserta · quem observa o EFEITO numa rota que executa código. Conserto reversível por construção. Juiz ADIADO ao post-mortem |
| 📦 **LOTE LOCAL** · destilação, garimpo, varredura em volume | ❌ | trabalho que custaria API roda num chat dedicado do Claude Code, com o mesmo código do produto (nunca motor paralelo), escrevendo nas mesmas tabelas, e o relatório diz quantas linhas entraram e por qual escritor |

```
📝 CONVERSÃO — o que a SPEC pronta TEM:
   card da conversão (§0.2) · BLOCO 0 que manda remedir · §7.3 com as referências ·
   todo número com comando (§0.4) · todo bloco com gate e mutação · O QUE SAIU da
   proposta, com o gatilho que a faz voltar · pendências · caixa do Founder
⛔ converter e executar em seguida. Nunca converter o que não vai executar nesta leva
```

---

## 9. 🔴 A LICENÇA DE AUTONOMIA

```
① O TESTE DO PRODUTO (§2)?          NÃO muda → PENDÊNCIA, e SEGUE
② Uma das oito do CLAUDE.md §10?    NÃO → não é motivo de parada
③ Precisa da MÃO do Founder?        SIM → CAIXA DO FOUNDER, e SEGUE
Só para se os três derem SIM e o próximo bloco for IMPOSSÍVEL, não incômodo.
🔴 dúvida entre caminhos: dê nota 0–100 a cada um, escolha o maior, registre, siga
🔴 travou 30 min? escolha o mais conservador, anote na caixa, siga
≤30 min E ≤2 arquivos E sem decisão a tomar → conserta e anota. Fora disso → pendência
```

### 9.1 O VALOR MARGINAL
```
🔴 MATERIAL — continua       segurança · isolamento · integridade · efeito colateral
                             errado · Core · aceite não provado · regressão · falha real
⛔ NÃO MATERIAL — pendência  estilo · micro-refactor · nome · abstração · doc que
                             ninguém precisa · dívida sem efeito hoje · gosto do juiz
🧑 2h → 93 sem defeito material  VENCE  24h → 95 de polimento
   6h → 99 fechando risco no Core VENCE  2h → 85 com fragilidade estrutural
```

### 9.2 A FAIXA DE RELÓGIO
Estourou a faixa do card? Não para. Responde por escrito **POR QUE CONTINUAR**: o que
falta · que risco fecha · que gate fecha · que evidência falta. Resposta "dá para
melhorar mais" → pendência.

### 9.3 ATIVIDADE NÃO É PROGRESSO
```
dois destes bastam: o mesmo blocker em duas rodadas sem evidência nova · nenhum gate
mudou de estado · patch feito e desfeito · a discussão cresce e o artefato não
→ PARE o laço · registre o provado e o tentado · CONTEXTO FRESCO · troque a ESTRATÉGIA
⛔ travamento nunca transforma FAIL em PASS
```

### 📋 A CAIXA DO FOUNDER
Seção do relatório que o executor vai acrescentando. Cada item: o que é · o que faz ·
o que custa esquecer · bloqueia? (quase sempre NÃO). Nunca se para para entregar uma linha dela.

---

## 10. 🔴 A MECÂNICA — mesmo trabalho, metade do relógio

```
MODELO      🎯 orquestrador = Fable 5.1.  Todo subagente = Opus 5 (builder, juiz,
            pesquisador, aquecimento, red team, auditor). Effort alto para juiz.
            ⛔ não trocar model nem effort no meio da sessão (zera o cache)
PAINEL      UM ÚNICO agent type, variando só o PROMPT · roda no diretório principal,
            sem worktree · em PARALELO, de uma vez, pela ferramenta de workflow
            quando houver 3+ lentes · `subagentPromptCacheTtl: "1h"`
FORK        só para auxiliares do executor. ⛔ nunca para juiz
BATERIA     a suíte INTEIRA roda no gate de cada bloco e no fim: 2 a 4 vezes por
            SPEC, nunca a cada commit. Parciais (um arquivo, um teste) à vontade.
            🔴 o relatório traz a contagem (diário do conftest)
MUTAÇÃO     roda em WORKTREE PRÓPRIO ou com lock exclusivo · restaura por CÓPIA,
            nunca `git checkout` · xfail nunca num guarda que lança processo
COMMIT      arquivo por arquivo. ⛔ nunca `git add -A`
ENTREGA     `git push origin HEAD:main` com a saída colada no relatório. Depois o
            Founder clica Implantar. Commit local não é entrega.
```

```
⛔ onde a velocidade NÃO está: builders paralelos que escrevem · agent teams para
   orquestrar · um "modo rápido" a mais · painel maior que 5
```

---

## 11. A TELEMETRIA — cinco linhas, no §0.1 do relatório

```
começou / terminou · tempo até a PRIMEIRA linha de código de produto
rodadas de painel e achados por lente (quantos foram ÚNICOS)
defeitos que o painel NÃO pegou e quem pegou
rodadas da bateria: inteiras · parciais · minutos esperando
nota 0–100 do orquestrador para a execução, com a justificativa em uma linha
```

---

## 12. QUANDO NÃO SE APLICA

```
❌ nível LEVE com SUPERFÍCIE 0 — faz e pronto (o verificador mecânico ainda roda)
❌ consulta pontual (§3.3)
❌ não substitui o CLAUDE.md: as regras invioláveis vencem
❌ não substitui a SPEC: ela diz O QUE, este diz COMO
❌ não é para ser lido inteiro toda vez. §0–§3, §5 e §7.3 resolvem 90%
```

## 13. QUEM DECIDE

**O orquestrador, sozinho, sempre.** O Founder nunca precisa pedir. Se precisar, o
protocolo falhou. Quando uma regra daqui errar duas vezes seguidas, muda-se o número e
registra-se por quê em [`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md).
