# PROTOCOLO AUTOBROKERS AAA

> **Como se executa, se julga e se autoriza a entrega de uma SPEC no AutoBrokers.**
> Não diz **o que** construir (isso é a SPEC). Diz **como construir, julgar, entregar e parar**.
>
> **v12.1 · AAA FAST · 17/09/2026** · vale para toda SPEC, execução, ideia, incidente e
> agente. Só regras. O porquê, com as medições: [`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md).

---

## 0. A REGRA DE UMA LINHA

> ## Quem escreve é um só. Quem julga não viu escrever. Quem estoura o relógio não chama mais ninguém.
> ## E nada trava o projeto por um defeito que não muda o produto.

## 0.1 ⛔ ESTE PROTOCOLO É LEI, E ELE SE CARREGA SOZINHO

```
1. O EXECUTOR lê este protocolo UMA vez. TODO pacote a subagente (juiz, lente, investigador)
   carrega §0–§3, §5 e §7.3. Sem ele, o agente NÃO COMEÇA.
2. TODO relatório ABRE com o EXECUTION CARD (§0.2) e FECHA com a telemetria (§11). Sem eles = SPEC aberta.
3. O guarda `backend/tests/test_o_protocolo_tem_policia.py` confere 1 e 2 por máquina.
```

## 0.2 🔴 O EXECUTION CARD — antes de escrever código, em 12 linhas

```
OUTCOME ..............  o que muda para quem usa
RISCO ................  0–8   (§3)
SUPERFÍCIE ...........  0–3   (§3)
PISO APLICADO ........  qual, e por quê (§3.2)
NÍVEL ................  LEVE · PADRÃO · CRÍTICO (§3.1) · executor e effort · juiz (nenhum · Opus · Fable)
UNIDADES .............  quantas, quais, e as FATIAS (§5.2)
COESÃO ...............  o que fica JUNTO e por quê (§3.4)
PARALELISMO REAL .....  "nenhum" — a escrita é de um só (§4)
TIME .................  executor · juiz · peças de ESCALAÇÃO e o GATILHO (§8)
REFERÊNCIA ...........  o artefato que o juiz vai ABRIR (§7.1) + a EXTERNA (§7.3)
GATES ................  o que precisa ficar verde
O ELO ................  a afirmação-título liga A a B? então MEDIU O ELO (§0.3)
FAIXA DE RELÓGIO .....  faixa, nunca promessa (§9.2) · tetos de turno e contexto (§10)
```

## 0.3 🔴 O ELO — duas medições certas não fazem uma causa certa

```
a afirmação é da forma "A acontece PORQUE B"?
   medi A?  ·  medi B?  ·  🔴 medi que B CHEGA em A?   ← o passo que ninguém dá
```

```
código morto (um return/if acima da linha culpada) → rode o caminho, ou leia da linha 1 da função até ela
meia regra (a regra é A E B, só A foi contado)     → conte cada cláusula separada
fonte de ontem (quem escreve mudou de tabela)      → pergunte "quem É o escritor HOJE"
```

## 0.4 🔴 A REGRA DO COMANDO — afirmar por leitura o que só um comando decide é defeito

```
todo número sobre código ou banco vem com o COMANDO ao lado, na mesma linha ou na seguinte
   linhas, contagens, datas → wc · grep -c · git log --diff-filter=A
   "existe" / "é o escritor" / "está no finally" → mostre a linha e as 3 acima dela
🔴 mudou um número, caminho ou faixa? `grep` do valor ANTIGO no arquivo inteiro. Sobrevivente = defeito
🔴 o juiz REPRODUZ por amostra: 3 números ao acaso por artefato. Um errado reprova a amostra inteira
```

---

## 1. 🔴 A DIETA — o agente recebe um PACOTE, nunca o canon

```
🔴 ESTE PROTOCOLO (§0–§3, §5, §7.3) — o PRIMEIRO item de todo pacote a subagente
+ o card (§0.2) e o contrato da SPEC (o que muda, o que não pode mudar)
+ o DIFF, os comandos dos gates e a LISTA DE ATAQUES (§6) — para o juiz
+ as regras invioláveis PERTINENTES, por número (CLAUDE.md §)
+ a REFERÊNCIA interna (§7.1) e a EXTERNA (§7.3) que o juiz vai abrir
+ as pendências POR NÚMERO — nunca o PENDENCIAS.md inteiro
+ o MODELO do agente (§10)
```

```
⛔ nenhum pacote manda "leia o protocolo INTEIRO"
⛔ o EXECUTOR lê a FICHA da SPEC (≤ 15 KB) e a proposta só por unidade; research pack só quando citado
🔴 proposta ≤ 40 KB · relatório ≤ 15 KB · este documento ≤ 22 KB. O guarda mede.
```

Pacotes-modelo em [`docs/canon/pacotes/`](pacotes/); prompt do executor em [`PROMPT-EXECUCAO-AAA-FAST.md`](PROMPT-EXECUCAO-AAA-FAST.md).

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
NÃO  →  PENDÊNCIA. Registra, e SEGUE. "é pequeno" não é argumento.
```

**Quem drena:** toda SPEC fecha ou re-justifica as pendências que toca:
`FECHADA` (com a prova) · `CONTINUA` (com o que destrava) · `MORREU`.

---

## 3. DUAS CONTAS, UM NÍVEL

🔴 **O RISCO diz SE precisa de juiz. A SUPERFÍCIE diz de que MODELO e quantas peças de escalação.**

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
NÃO SEI ONDE PEGA → SUPERFÍCIE (investigador read-only) · NÃO SEI SE O MODELO OBEDECE → PROVA
UNIDADE = a menor coisa que dá para ENTREGAR e PROVAR sozinha. FATIA = o que cabe numa sessão (§5.2)
```

### 3.1 O NÍVEL — a tabela inteira cabe em três linhas

| nível | quando | executor | juiz fresco (§6) | rodadas |
|---|---|---|---|---|
| **LEVE** | RISCO 0–1 e SUPERFÍCIE 0–1 | Opus 5 `medium`/`high` | nenhum (só o verificador mecânico) | 0 |
| **PADRÃO** | RISCO 2–5, ou SUPERFÍCIE 2 | Opus 5 `high` | **Opus 5** | 1 |
| **CRÍTICO** | RISCO 6+, ou SUPERFÍCIE 3, ou o piso da §3.2 | Opus 5 `xhigh` | **Fable 5.1** · + confirmação e lente por gatilho (§8) | 1 (+1 curta) |

```
⚠️ rótulo e soma discordam? a soma vence
⛔ LEVE dispensa o JUIZ. Nunca o verificador mecânico (passo ③ da §5)
🔴 effort NÃO é alavanca de custo (a saída é ≈6 % do gasto). Baixa-se turno e contexto (§10)
```

### 3.2 🔴 O PISO — por EFEITO, nunca por tipo de arquivo

```
CRÍTICO no mínimo, independente da conta:
 · qualquer coisa que ENVIE      mensagem, acionamento, chamado, cobrança
 · migration que ALTERA DADO, ESTRUTURA, TRAVA ou QUEM PODE LER
   ⚠️ só o COMMENT é isento. Índice e GRANT disparam
 · autenticação, sessão, ou o filtro `company_id`
 · ler de uma corretora e escrever noutra
🧑 "isto é mais importante do que parece" → CRÍTICO ou ESCALAÇÃO (§8). Sem a contrária
```

### 3.3 A conta vale para MUDANÇA, não para INVESTIGAÇÃO

```
CONSULTA PONTUAL  "onde está X?" · "o que faz Y?"        → dispensado
VARREDURA         "isto funcionou?" · "serve para nós?"  → MODO INVESTIGAÇÃO (§8)
```

### 3.4 A COESÃO — decide o que fica junto na mesma FATIA

```
tocam a MESMA interface, tipo ou contrato? uma REDEFINE o que a outra consome? mesmo ARQUIVO-HUB? → juntas
```

---

## 4. OS PAPÉIS — dois por padrão; o resto por gatilho

```
🔧 EXECUTOR       Opus 5, SESSÃO NOVA por SPEC ou fatia. Lê, mede, escreve TODO o código, prova,
                  chama o juiz, conserta, entrega, REGISTRA. 🔴 a escrita é dele só
⚖️ JUIZ FRESCO    subagente read-only, contexto limpo, que não viu escrever (§6)
⚙️ VERIFICADOR    passo mecânico do laço, não papel convocado
🔍 INVESTIGADOR   Sonnet 5, read-only, no máximo UM, só para varredura grande e paralela
— por GATILHO (§8) —  🔬 LENTE DO DADO (reconstrói o outcome por SELECT) · 🗡️ RED TEAM (Fable 5.1, missão:
QUEBRAR) · 🏁 CONFIRMAÇÃO (juiz novo, ≤ 20 turnos, só o diff do conserto)
🎯 FABLE          decide, audita e escreve protocolo em OUTRO chat. Nunca turno a turno
```

**O verificador mecânico**, na ordem: `py_compile`/`tsc` · testes do bloco · lint · migrations pelo
VERIFY (o ledger mente; confere o OBJETO) · regressão dirigida. 🔴 Mexeu em `app/`, `middleware.ts`,
`next.config.js` ou env: `npm run test:rotas-montam` + `next start` + UMA requisição a `/api/…`.

```
⛔ DELEGAÇÃO: não delegue o que termina em poucas chamadas · nem a verificação do PRÓPRIO trabalho ·
   nenhum builder A/B/C/D · nenhum orquestrador.  Todo subagente reporta o que vir FORA do escopo
```

---

## 5. O LAÇO — seis passos, uma volta

```
① CARD + BLOCO 0 MÍNIMO   ≤ 15 min · 5–10 premissas que mudariam o DESENHO, comando ao lado (§0.4)
② BUILD                   UM escritor, fatia por fatia, commit por fatia (arquivo por arquivo, nunca -A).
                          Guarda novo nasce VERMELHO e fica VERDE (linha de controle)
③ VERIFICADOR MECÂNICO    §4 · mutação dos guardas NOVOS, uma vez  →  FAIL volta ao ②, nunca ao juiz
④ JUIZ FRESCO             uma passada sobre o diff acumulado, o teste rodando e o banco (§6).
                          🔴 outcome é NÚMERO ou DATASET? a LENTE DO DADO entra pelo gatilho (§8)
⑤ CONSERTO ÚNICO          o EXECUTOR aplica o TESTE DO PRODUTO a cada achado, conserta TUDO junto,
                          reroda SÓ os gates afetados. Achado não consertado vira pendência escrita
⑥ ENTREGA                 suíte inteira UMA vez em 2º plano, triada por DIFF · relatório ≤ 15 KB · push com a
                          saída colada · telemetria (§11). Dossiê fora do caminho
```

### 5.1 O JUIZ JULGA CÓDIGO
```
⛔ NÃO se monta juiz sobre uma SPEC nem sobre documento
✅ o juiz roda sobre o diff, o teste rodando, o banco
```

### 5.2 As FATIAS — uma SPEC grande, UMA sessão, e o builder fresco a partir da 2ª fatia
```
≥ 3 unidades ou > 40 KB → FATIAS INTERNAS: mesma SPEC, branch, relatório e SESSÃO. fatia = ② → ③ → commit.
O executor constrói a fatia 1. Da fatia 2 em diante, DELEGA a construção a UM builder subagente
fresco (Opus 5 xhigh, sequencial) com o pacote (card · unidades · arquivos · handoff · gates). O executor fica como gerente: provas, juiz, conserto. O juiz roda UMA vez, no fim.
⛔ nunca sessão nova por fatia nem Founder trocando de chat · nunca dois builders ao mesmo tempo
```

### 5.3 Nunca a mesma lente duas vezes
```
⛔ JUIZ RETOMADO É PROIBIDO: julga os próprios achados e dá nota alta falsa
⛔ segunda rodada só pelo gatilho da §8. Rodadas extras compram falsos positivos
```

### As portas
```
✅ o juiz libera, ou só sobraram pendências  →  registra e entrega
🛑 reprovou DUAS vezes com blocker material  →  ESCALAÇÃO (§8); é uma das oito do CLAUDE.md §10?
      SIM → para e registra   ·   NÃO → entrega o que passou e AVANÇA
⛔ NUNCA: afrouxar a régua · alterar teste para passar · pronto por cansaço
🔴 lista de casos fixados carrega PARES: mesma superfície, veredito oposto
```

---

## 6. O JUIZ

```
RECEBE   o card · o contrato da SPEC · o DIFF · os comandos dos gates · a referência · a LISTA DE ATAQUES
NUNCA    a narrativa do executor · o esforço · "está funcionando" · o resumo
ATAQUES  dado vazio/nulo · duas corretoras ao mesmo tempo (company_id) · a mesma mensagem 2× (idempotência) ·
         dois processos ao mesmo tempo · rollback da migration · o produto CHAMA este caminho? (rode-o) ·
         regressão direta do diff · efeito externo (mensagem, portal, dinheiro)
Presuma FAIL até existir evidência de PASS. Cite arquivo, linha, comando, saída ou consulta em CADA
conclusão. Reproduza 3 números por amostra (§0.4). Não reroda todas as mutações.
🔴 Se estiver bom, diga que está bom. Juiz que precisa achar defeito para se justificar É o defeito
FORMA: VEREDITO · BLOCKERS (com o teste do produto) · PENDÊNCIAS · EVIDÊNCIA · MAIOR LACUNA ·
       PRÓXIMA AÇÃO · CONFIANÇA e o que ficou por medir · NOTA
⚖️ o juiz CLASSIFICA · 🔧 o executor REGISTRA e decide. Rebaixou um blocker? a discordância vai
   ESCRITA. Não se rebaixa segurança, isolamento, P0/P1 do CLAUDE.md §10
🔴 PRESCRIÇÃO NÃO É MEDIÇÃO: o achado vem com a medição; o executor reproduz antes de aplicar
```

### 6.1 CONFIRMAÇÃO — depois do conserto, só por gatilho (§8)
```
juiz NOVO do mesmo modelo, ≤ 20 turnos, SÓ o diff do conserto. Missão única: "o conserto criou defeito?"
```

---

## 7. A REFERÊNCIA — o que substitui "faça excelente"

```
1. INSPECIONÁVEL   o juiz ABRE, RODA ou MEDE. Se só imagina, é adjetivo
2. UM PONTO        "como o Linear faz o estado vazio", nunca "no nível do Linear"
3. A INTERNA VENCE A EXTERNA — a MEDIANA do que passou no gate
4. UMA POR DIMENSÃO, com NOME e CAMINHO
🔴 sem referência inspecionável, a dimensão é "NÃO AVALIADA" — nunca "aprovada"
```

### 7.1 AS REFERÊNCIAS INTERNAS — abra, rode, compare

| dimensão | referência, por caminho | como o juiz compara |
|---|---|---|
| **UI / design** | `docs/canon/DS-001-design-brief.md` §5 | item a item contra ChatGPT · Claude |
| **multi-tenant** | `CLAUDE.md` §7 + teste com **dois tenants reais** | o filtro no código, não a RLS |
| **migration** | `docs/canon/MIGRATIONS-AUTHORITY.md` | APPLY · VERIFY · ROLLBACK escritos ANTES |
| **um guarda serve?** | `CLAUDE.md` §9.3 + linha de controle | prove que ele CONSEGUE ficar vermelho |
| **o build sobe?** | `CLAUDE.md` §9.1 | `next start` + uma requisição a `/api/…` |
| **o número é medido?** | `CLAUDE.md` §12.1 + §0.4 daqui | 📊 tem comando e data · 💭 não é citável |
| **corredor / rota** | `backend/scripts/medir_rota.py --com-espelho` | número contra número |
| **rota de referência** | `allianz/auto/guincho` | a rota nova chega perto? |
| **atendimento ponta a ponta** | `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py` | a sessão real, turno a turno |
| **conversas-ouro** | `backend/tests/test_golden_do_eletricista.py` | casos lidos do banco de produção |
| **telas reais de URA** | `backend/tests/corpus/telas_reais/` | o texto vem do acervo, não da imaginação |

⛔ **O que NÃO temos, declarado:** tela do dashboard designada como padrão · guarda
de UI · arquivo OpenAPI · alvo de latência (SLO) · OWASP aplicado a um julgamento.
Nessas dimensões o veredito é "não avaliada".

### 7.2 Referência OBSERVADA registra o que foi feito, não o que se deve fazer
Identidade, dinheiro e escolha-entre-existente-e-novo exigem julgamento humano.

### 7.3 🔴 A REFERÊNCIA EXTERNA — como a pesquisa entra numa SPEC

```
🔴 toda SPEC tem a seção "O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS"
   com 3 a 7 referências externas, cada uma em quatro linhas:
      URL · o que ela faz · o que MODELAMOS dela (um ponto) · o que REJEITAMOS e por quê · COMO O JUIZ INSPECIONA
🔴 a fonte é a PROPOSTA. Na execução NÃO se pesquisa de novo; o juiz reabre o que a unidade cita
🔴 "o padrão do mercado" não é referência. Repositório, doc oficial, tela, paper: é
⛔ referência externa nunca vira autoridade: as peças do CLAUDE.md §5 continuam únicas. Modela-se o PADRÃO
🔴 o guarda conta: SPEC ≥ 088 sem 3 URLs externas na seção não fecha
```

---

## 8. OS MODOS — e a ESCALAÇÃO

| modo | a conta governa? | elenco mínimo |
|---|---|---|
| 🧭 **INVESTIGAÇÃO** · ideia, auditoria, medição | ❌ (§3.3) | medidor · cético · juiz do risco. Teto 4 frentes. SAÍDA: estado · quebrado · o que destrava · **o que ficou por medir** |
| 🔨 **EXECUÇÃO** | ✅ por unidade | AAA FAST: executor + juiz pelo nível (§3.1). Escrita de UM SÓ. Fatias em série |
| 🤖 **AGENTE** · Central, auto-evolução | ✅ + três travas | teto de voltas · teto de custo · o que muda é reversível e registrado |
| 🚨 **INCIDENTE** | ❌ | quem conserta · quem observa o EFEITO numa rota que executa código. Juiz ADIADO |
| 📦 **LOTE LOCAL** · garimpo em volume | ❌ | chat dedicado, mesmo código do produto, mesmas tabelas |

**ESCALAÇÃO — só por gatilho escrito no card ou na caixa do Founder:**

| peça | entra quando (qualquer um) |
|---|---|
| **lente do dado** | outcome é NÚMERO, DATASET ou relatório que a corretora lê · migration que ALTERA DADO · a SPEC afirma percentuais do acervo |
| **confirmação (§6.1)** | o juiz achou ≥ 1 BLOCKER em código que ENVIA, filtra `company_id` ou grava por migration |
| **red team dedicado** | autenticação/sessão · cross-tenant · dinheiro · ação irreversível a terceiro |
| **consulta ao Fable antes do BUILD** (≤ 15 turnos) | decisão de arquitetura em aberto |
| **segundo juiz** (família diferente) | o primeiro reprovou com ≥ 2 blockers materiais E a SPEC envia ou toca tenant |
| **AAA COMPLETO** (painel de 3 lentes + red team + lente + confirmação) | incidente P0/P1 · mudança ampla de arquitetura · migration DESTRUTIVA · o Founder disse "é mais importante do que parece" · o juiz reprovou DUAS vezes com blocker material |

```
⛔ nunca entram: aquecimento de perguntas · conversão · pesquisador · integrador · builders paralelos · orquestrador
🔴 nenhuma peça entra no laço PADRÃO sem blocker EXCLUSIVO medido em 2 SPECs, registrado em EVIDENCIAS
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
🧑 2h → 93 sem defeito material VENCE 24h → 95 de polimento · 6h → 99 fechando risco no Core VENCE 2h → 85 frágil
```

### 9.2 A FAIXA DE RELÓGIO
**1,5× a faixa** do card sem blocker aberto? Para de construir, entrega a fatia verde, registra o
que resta. ⛔ **A resposta a "estourou" NUNCA é "mais um agente".** "Dá para melhorar" → pendência.

### 9.3 ATIVIDADE NÃO É PROGRESSO
```
dois destes bastam: o mesmo blocker em duas rodadas sem evidência nova · nenhum gate
mudou de estado · patch feito e desfeito · a discussão cresce e o artefato não
→ PARE o laço · registre o provado e o tentado · CONTEXTO FRESCO · troque a ESTRATÉGIA
⛔ travamento nunca transforma FAIL em PASS
```

### 📋 A CAIXA DO FOUNDER
Seção do relatório. Cada item: o que é · o que faz · o que custa esquecer · bloqueia? (quase sempre
NÃO). Nunca se para para entregar uma linha dela.

---

## 10. 🔴 A MECÂNICA — o custo é turno × contexto

```
SESSÃO      UMA por SPEC, do card ao push, contexto nascendo vazio. CLAUDE.md + memória + a FICHA da SPEC +
            BLOCO 0 são o aquecimento. ⛔ nenhuma sessão executa duas SPECs · ⛔ nenhuma SPEC em duas sessões
MODELO      🔧 executor = Opus 5 (LEVE medium/high · PADRÃO high · CRÍTICO xhigh) · ⚖️ juiz = Opus 5 em PADRÃO,
            Fable 5.1 em CRÍTICO · 🔍 investigador = Sonnet 5 · 🗡️ red team = Fable 5.1. ⛔ não trocar no meio
TETOS       LEVE · PADRÃO · CRÍTICO — turnos do executor ≤ 80 · 160 · 250 por fatia · contexto ≤ 200 · 250 · 300 k
            (passou, a próxima fatia vai ao builder §5.2) · agentes além do executor 0 · 1 · 2 + builders (§5.2) · relógio ≤ 40 min ·
            75 min · 2h30 (fatia ≤ 1h15) · juiz ≤ 80 turnos e ≤ 250 k
APLICAÇÃO   env CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=2 · CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1 (.claude/settings.json) ·
            hook bloqueia o 8º agente (`.claude/hooks/teto-de-agentes.py`) · status line conferida em CADA gate ·
            o script da §11 fecha a conta
JUIZ RECEBE o card + o diff + os comandos + a lista de ataques. Nunca a SPEC inteira nem o censo
CACHE       `subagentPromptCacheTtl: "1h"` · juiz no diretório principal, nunca FORK
BATERIA     a suíte INTEIRA roda UMA vez por SPEC, em 2º plano, triada por DIFF contra a linha de base
            versionada. Parciais à vontade. 🔴 o relatório traz a contagem (diário do conftest)
MUTAÇÃO     só nos guardas NOVOS, uma vez · WORKTREE PRÓPRIO ou lock · restaura por CÓPIA · xfail nunca em guarda com processo
COMMIT      arquivo por arquivo · cada fatia salva COMPLETA antes da seguinte. ⛔ nunca `git add -A`
ENTREGA     `git push origin HEAD:main` com a saída colada. Depois o Founder clica Implantar
```

---

## 11. A TELEMETRIA — oito linhas, no fim do relatório, pelo script

```
python backend/scripts/medir_execucao_claude_code.py --sessao atual
relógio total e por fase ①–⑥ · turnos e contexto de pico por agente · tokens de contexto e saída ·
US$ API-equivalente por agente e total · nº de agentes · achados por mecanismo (executor · prova
mecânica · juiz · lente · canário), com EXCLUSIVO em cada blocker · rodadas da bateria · nota 0–100
do executor (critério em 1 linha) e do juiz
```

## 12. QUANDO NÃO SE APLICA

```
❌ nível LEVE com SUPERFÍCIE 0 — faz e pronto (o verificador mecânico ainda roda) · consulta pontual (§3.3)
❌ não substitui o CLAUDE.md (as regras invioláveis vencem) nem a SPEC (ela diz O QUE, este diz COMO)
❌ subagente não lê inteiro: §0–§3, §5 e §7.3 resolvem 90%
```

## 13. QUEM DECIDE

**O executor, sozinho, sempre.** O Founder nunca precisa pedir.
Regra que errar duas vezes muda de número, com o porquê em [`PROTOCOLO-AAA-EVIDENCIAS.md`](PROTOCOLO-AAA-EVIDENCIAS.md); nunca acrescenta papel.
