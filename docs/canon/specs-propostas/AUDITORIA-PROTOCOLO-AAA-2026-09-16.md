# AUDITORIA DO PROTOCOLO DE EXECUÇÃO — AAA v11.2, laço curto e a proposta "AAA FAST 1+1"

> **16/09/2026 · Fable 5.1 · modo INVESTIGAÇÃO (protocolo §8).** Pedido do Founder: auditoria
> completa do custo e do tempo das execuções, validação independente das duas análises do
> ChatGPT, e um protocolo definitivo que preserve a qualidade e corte muito o consumo.
> Nada foi executado; nenhum documento canônico foi alterado. Esta auditoria e os três
> arquivos irmãos ficam em `specs-propostas/` até o Founder decidir.
>
> **Fonte primária de todos os números 📊 desta auditoria:** os transcritos reais do Claude
> Code em `~/.claude/projects/c--Users-amand-Projetos-AUTOBROKERS-RESULTA-AutoBrokers-FIX/`
> (arquivo `.jsonl` da sessão + `<sessão>/subagents/agent-*.jsonl`), lidos pelo script
> [`AAA-FAST-medir-execucao.py`](AAA-FAST-medir-execucao.py), cruzados com `git log` e com os
> relatórios em `docs/canon/reports/`. Nenhum número abaixo veio de memória ou de relatório
> sem ter sido reproduzido no transcrito.

---

## 0. A resposta em uma página

```
O QUE O FOUNDER VIU        SPEC de 6–15 h, "milhões de tokens", o plano acabando antes da semana.
O QUE A MEDIÇÃO MOSTRA     📊 relógio real: 001.6 = 4h48 · 001.1 = 9h16 · 001.2 = 5h03.
                           Os relatórios declararam 9 h · 15 h · 8 h. Eles ERRAM PARA CIMA
                           (mistura de fuso local com UTC). O problema existe, mas é menor
                           do que parece, e tem forma diferente da imaginada.

                           📊 "1,45 M / 2,9 M tokens de subagentes" NÃO É CONSUMO. É a soma do
                           TAMANHO FINAL DO CONTEXTO de cada agente (o número que o "Agent map"
                           do Claude Code mostra). O consumo real é outra grandeza:
                           turnos × contexto. A 001.2 processou 📊 198 M tokens de contexto
                           só nos subagentes (+ ≈110 M no orquestrador Fable).

ONDE O CUSTO ESTÁ          1º  o ORQUESTRADOR Fable, com contexto de 900 k–980 k tokens, que
                               relê tudo a cada turno e não escreve código: ≈ metade do custo
                               de cada SPEC, invisível nos relatórios.
                           2º  agentes que fazem 350–490 turnos (o conserto da 001.1: 395
                               turnos, US$ 71 de API-equivalente sozinho).
                           3º  o FECHAMENTO documental: 21–28 % do relógio de cada SPEC.
                           4º  propostas de 96–124 KB + research pack de 25–75 KB por SPEC.
                           O painel de juízes custa 📊 4–7 % do relógio e 3–10 % do dinheiro,
                           e é quem acha os blockers. O laço curto cortou o que era barato e
                           manteve o que era caro — por isso não ficou curto.

O QUE FAZER                AAA FAST: UM executor Opus 5 numa sessão NOVA por SPEC (sem
                           orquestrador) · provas mecânicas · UM juiz adversarial FRESCO
                           (Fable 5.1 em CRÍTICO, Opus 5 em PADRÃO) · UM conserto · entrega.
                           Lente do dado, segundo juiz, red team separado e AAA completo só
                           por gatilho escrito. Tetos em TURNOS e CONTEXTO, aplicados por
                           hook e por env do Claude Code, não por frase no relatório.

O QUE ESPERAR (💭 alvo)    CRÍTICO do tamanho da 001.2: 2h–2h30 e ≈ 1/3 do custo medido.
                           PADRÃO: ≤ 75 min. LEVE: ≤ 40 min. Qualidade: 88–92 em CRÍTICO,
                           igual à do laço curto (que se deu 84–87), não menor.
                           95–98 em toda SPEC NÃO é promessa que a evidência sustente.
```

---

## 1. AUDITORIA DA TESE DO CHATGPT — o que está certo, errado e incompleto

| afirmação do ChatGPT | veredito | evidência |
|---|---|---|
| "O laço curto falhou em resolver o problema" | **CERTO no efeito, ERRADO na medida** | 📊 relógio real 4h48 / 9h16 / 5h03 (não 9 / 15 / 8). Custo API-equivalente dos subagentes: 001.6 US$ 80 · 001.1 US$ 205 · 001.2 US$ 114 — contra 095 US$ 74 · 096 US$ 93 · 098 US$ 167 sob AAA completo. **O laço curto não cortou custo; cortou um pouco de relógio.** |
| "Os tokens de subagentes estouraram o teto de 1 M em 80–190 %" | **ERRADO: a grandeza não existe** | Os números por agente nos relatórios são o **contexto final** de cada subagente (📊 juiz da 001.2: relatório 199k · transcrito 193k de contexto no último turno; conserto 317k · 313k; Builder DF 289k · 286k). Nenhum teto em "tokens" assim definido mede consumo. Ver §2.1. |
| "Um executor forte + um juiz independente forte + um conserto" | **CERTO — e é o que a evidência do próprio projeto já dizia** | 📊 001.2: o juiz fresco (33 turnos, 11 min, ≈US$ 3) achou os 2 blockers reais; os 4 builders + orquestrador custaram ≈US$ 130 para chegar ali. `PROTOCOLO-AAA-EVIDENCIAS.md`: "juiz de contexto limpo: nota 98, 4 defeitos exclusivos que quebrariam produção". |
| "Escrita single-threaded; subagentes só read-only" | **CERTO** | Cognition (22/04/2026): "writes stay single-threaded, additional agents contribute intelligence". Anthropic (doc do Opus 5): "não delegue o que termina em poucas chamadas; não use subagente para verificar o próprio trabalho". 📊 Na 001.1 os 5 builders tocaram `infocap_tool.py`/`nodes.py` em SÉRIE (card: "B → C → D serial") — o paralelismo real foi ≤ 2 e comprou pouco relógio. |
| "Opus 5 High executor, Fable 5.1 juiz fresco" | **PARCIALMENTE CERTO** | Anthropic mede Opus 5 a 0,5 % do pico do Fable 5 no CursorBench por metade do custo; e "Opus 5 revisa código com alta precisão e recall; a acurácia se mantém em effort baixo". Mas: (a) o Fable 5.1 é sucessor do Fable 5, mais forte; (b) o custo de effort é **marginal** aqui (📊 saída = 1,36 M de 860 M tokens da sessão de 3 SPECs → ≈6 % do custo), então **xhigh** no executor é barato — o que custa é turno, não pensamento. Ver §3. |
| "Fable como orquestrador acompanhando tudo é o erro" | **CERTO, e é a maior causa medida, que o ChatGPT só intuiu** | 📊 o orquestrador Fable das 3 EXTRA-001.x: 347 turnos com contexto de pico **963 k**, 170 M tokens de contexto processados, ≈US$ 137 — mais que os subagentes de qualquer SPEC individual. Ele não escreveu uma linha de produto. Ver §2.2. |
| "Suíte inteira fora do caminho crítico" | **CERTO com ressalva** | 📊 a suíte inteira leva 25 min e já roda em segundo plano; o que custa é a **triagem** das 14–24 falhas pré-existentes a cada SPEC (repetida 3× em 3 SPECs) e as baterias `--mutar` (📊 001.1: "1h45 em baterias --mutar" dentro do conserto). |
| "BLOCO 0 de 5–15 min" | **JÁ É ASSIM** | 📊 001.2: prompt 18:10Z → commit do BLOCO 0 18:21Z (11 min). 001.6: 16 min. O BLOCO 0 não é o custo. |
| Orçamento por fase 90–120 min em CRÍTICO grande | **OTIMISTA para o tamanho das EXTRA-001.x** | 📊 só o BUILD da 001.2 somou 145 min de builders (4 unidades, 2 migrations, 12 guardas). Um executor único faz o mesmo em 💭 100–130 min. Alvo honesto: **2h–2h30 numa fatia, ou 2 × 1h15**. |
| "Hard stop real durante a execução" | **CERTO, e o ChatGPT não diz COMO** | O Claude Code tem os mecanismos: `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, hooks `PreToolUse` que bloqueiam por contagem, status line com contexto. Ver §5. |
| "Documentação autoalimentada" | **CERTO, e maior do que o ChatGPT estimou** | 📊 001.2: fechamento 21:48Z → 23:13Z = **85 min (28 % do relógio)** para relatório (54 KB), PENDENCIAS, FOUNDER-DECISIONS, CHANGE-ADDENDA, ESTADO, INDICE, dossiê, 4 commits de docs. Proposta 124 KB + RP 75 KB + prompt 19 KB = 218 KB antes de qualquer código. |

**O que falta na tese do ChatGPT:** (1) a telemetria que ele usou é a errada, então as conclusões
sobre "estouro de tokens" são infundadas mesmo estando certa a direção; (2) não viu o orquestrador
como custo; (3) não separa **turnos** de **tokens** — e é o número de turnos que governa tudo; (4) não
diz como o teto se aplica; (5) não olha o fechamento documental, que é 1/4 do relógio.

---

## 2. CAUSA DO CUSTO — decomposição medida

### 2.1 🔴 A grandeza certa: turno × contexto

Cada turno de um agente reenvia o contexto inteiro (cache read a 10 % do preço, mas contando).
📊 Sessão das três EXTRA-001.x (`a4546c6b`, 13–14/09):

```
                          turnos   contexto   tokens de contexto   saída     API-equiv.
                                   de pico    processados (cache)
orquestrador Fable          347     963 k         169,9 M           795 k    US$ 137
21 subagentes Opus        3.150     142–456 k     860,4 M          1.360 k    US$ 536
```

Os **13 M de cache-write + 860 M de cache-read** são o custo. A saída (o que o modelo "pensa e
escreve") é **1,36 M tokens = US$ 34**. Conclusão que muda a estratégia: **effort alto é barato;
turno é caro.** Um agente com 350 turnos e 300 k de contexto custa o mesmo que 5 agentes de 70 turnos.

### 2.2 Por SPEC — o que a telemetria real mostra (📊 transcritos + `git log`)

| SPEC | protocolo | relógio REAL | declarado | agentes | subagentes (ctx-tokens · US$) | maior agente | orquestrador Fable |
|---|---|---|---|---|---|---|---|
| 095 | AAA completo | 6h20 | — | 6 | 122 M · **74** | motor 197 turnos | sessão de 4 SPECs: 307 M · US$ 241 |
| 096 | AAA completo | ≈16 h (1 queda) | 6–8 h | 14 | 169 M · **93** | frontend 178 turnos | idem |
| 097.1 | AAA completo | ≈11 h | — | 10 | 307 M · **176** | fix red team **488 turnos · US$ 88** | idem |
| 098 | AAA completo | ≈9 h | — | 17 | 279 M · **167** | desenhista 260 turnos · US$ 49 | 100 M · US$ 58 |
| EXTRA-001 | AAA opção B | ≈5 h (1 queda) | — | 10 | 331 M · **164** | desenhista 204 turnos | 208 M · US$ 90 |
| **001.6** | laço curto | **4h48** | 9 h | 6 | 131 M · **80** | builder A 164 turnos | sessão de 3 SPECs: 170 M · US$ 137 |
| **001.1** | laço curto | **9h16** (≈1 h sem tokens) | 15 h | 8 | 361 M · **205** | conserto **395 turnos · US$ 71** | idem |
| **001.2** | laço curto | **5h03** | 8 h | 7 | 198 M · **114** | builder E **357 turnos · US$ 55** | idem |

Preços de API usados: Opus 5 = 5 / 6,25 / 0,50 / 25 US$ por M (input · cache-write · cache-read ·
output); Fable 5.1 = 10 / 12,5 / 0,25 / 50. ⚠️ O plano de assinatura não cobra em dólar, mas pesa as
mesmas grandezas; o dólar é a régua comparável. 📊 Fonte das quedas: prompts "OS TOKENS ACABARAM"
em 04/09, 05/09, 07/09, 13/09 e 14/09 nos transcritos.

**Três leituras:**
1. **O laço curto não reduziu o custo.** A média por SPEC ficou em US$ 133 (laço curto) contra
   US$ 135 (AAA completo). Ele reduziu relógio (4h48–9h16 contra 6h–16h) porque tirou aquecimento,
   conversão e 3 lentes — as fases baratas em tokens mas serializadas no relógio.
2. **O que ele NÃO tirou é o que custa:** o orquestrador de 900 k, os builders de 300+ turnos e o
   fechamento documental.
3. **O juiz é o melhor negócio do laço:** 📊 001.2: juiz 33 turnos · 11 min · US$ 3,3 → 2 blockers reais
   (janela de 18 s virou padrão; rajada perdida no turno vencido). 001.6: juiz 15 min · US$ 9 → 2
   blockers; lente 20 min · US$ 6,5 → 2 blockers de dado. 001.1: lente 34 min · US$ 4,8 → 1 blocker
   que nenhum guarda via.

### 2.3 Onde o relógio vai dentro de uma SPEC (📊 001.2, 303 min; 001.6, 288 min)

```
fase                          001.2          001.6         quem
leitura + BLOCO 0             11 min   4 %   16 min   6 %  orquestrador
BUILD (builders em ondas)    126 min  42 %  128 min  44 %  4 builders / 3 builders + orquestrador no P0
handoffs entre ondas          12 min   4 %    5 min   2 %  orquestrador relê, monta pacote, espera
JUIZ + LENTE (paralelos)      11 min   4 %   21 min   7 %  2 subagentes
CONSERTO único                58 min  19 %   58 min  20 %  1 builder (9 achados / 4 blockers + 13 pend.)
FECHAMENTO                    85 min  28 %   61 min  21 %  suíte 25 min (2º plano) + triagem + 6 docs + dossiê + push
```

### 2.4 O custo documental

📊 Pacote lido antes da 1ª linha de código (001.2): proposta **124 KB** + research pack **75 KB** +
prompt individual **19 KB** + MODELO 4,5 KB + protocolo 22 KB + CLAUDE.md 30 KB = **≈275 KB ≈ 70 k
tokens**, relidos (parcialmente) por 7 agentes. O relatório saiu com **54 KB** (001.1: 77 KB;
001.6: 68 KB) e o fechamento tocou 6 documentos canônicos em 4 commits. O diagnóstico §13.4 já
decidira "proposta ≤ 40 KB" — a 001.3 pronta para executar tem **109 KB + RP 50 KB + prompt 20 KB**.

### 2.5 A regra que a evidência produz

> **Custo = Σ (turnos × contexto) por agente.** Reduzir agentes sem reduzir turnos e contexto não
> reduz custo. Reduzir effort quase não reduz custo. O que reduz: (1) nenhum orquestrador de 900 k;
> (2) sessão nova por SPEC com contexto ≤ 300 k; (3) agentes com teto de turnos; (4) menos
> documento entrando e saindo.

---

## 3. COMPARAÇÃO DE MODELOS

Fatos externos que pesam (fontes em §13):
- Anthropic: Opus 5 a **0,5 % do pico do Fable 5** no CursorBench, **metade do custo**; "melhor
  desempenho por custo em high, xhigh e max". Opus 5 "revisa código com alta precisão e recall; a
  acurácia se mantém em effort baixo". Doc de effort: "comece em high; suba a xhigh para coding e
  agentic exigentes; max quando a tarefa justificar gasto sem restrição".
- Anthropic (advisor, medido): **Opus 5 executor + Fable 5.1 advisor = configuração mais precisa
  medida**, +3,5 pontos sobre Opus 5 sozinho por preço igual ou menor; "Fable executor + Fable
  advisor: quase nada" (não há lacuna a explorar). O advisor é ferramenta de API; no Claude Code o
  equivalente é **um subagente Fable de contexto limpo**.
- "Nine Judges, Two Effective Votes" (arXiv 2605.29800): 9 juízes ≈ 2 votos independentes; o melhor
  juiz sozinho iguala ou supera o painel; **erros correlacionados** vêm da mesma família.
- "More Rounds, More Noise" (arXiv 2603.16244): revisão de uma passada (F1 0,376) > multi-rodada
  (0,303); rodadas extras geram **62 % mais falsos positivos**.
- Cognition (22/04/2026): revisor de contexto limpo acha ≈2 bugs por PR, 58 % graves; "smart
  friend" funciona quando os dois modelos são de fronteira.

Custo relativo (📊 na 001.2 o executor/builders são **≈85 %** do gasto de subagentes; o juiz **≈3 %**):

| arranjo | qualidade esperada | velocidade | custo relativo | risco | nota | quando |
|---|---|---|---|---|---|---|
| **Opus 5 xhigh executor → Fable 5.1 fresco juiz** | 90–93 | alta | 1,0 (juiz Fable ≈ +5 %) | juiz de família diferente = erros menos correlacionados; Fable tem cota própria | **92** | **CRÍTICO** |
| Opus 5 high executor → Opus 5 fresco juiz | 86–90 | alta | 0,95 | mesma família julga a mesma família | **86** | **PADRÃO** |
| Opus 5 medium/high → só provas mecânicas | 82–88 | muito alta | 0,6 | sem olhar independente | **84** | **LEVE** (sem envio, sem tenant, sem migration) |
| Opus 5 **max** executor → Fable juiz | 91–93 | média | 1,05–1,15 (mais turnos, não mais tokens de saída) | Anthropic: em max "custo significativo por ganho pequeno; pode pensar demais" | 88 | só se a SPEC for de raciocínio profundo (algoritmo, concorrência) |
| Fable 5.1 executor → Opus 5 juiz | 91–94 | média | ≈1,9 (executor é 85 % do gasto, a 2×) | juiz mais fraco que o escritor acha menos (Cognition) | 80 | não como padrão |
| Fable 5.1 executor → Fable 5.1 fresco juiz | 92–95 | média | ≈2,0 | "quase nada" a ganhar no par de fronteira; consome a cota Fable | 82 | ESCALAÇÃO: arquitetura incerta, concorrência distribuída |
| Fable advisor curto → Opus executor → Fable juiz | 91–94 | alta | 1,1 | no Claude Code o "advisor" é uma consulta manual antes do BUILD; útil só se houver decisão de arquitetura aberta | 88 | CRÍTICO com decisão de desenho não fechada na SPEC |
| Fable orquestra → N builders Opus → juiz (o atual) | 85–88 | baixa | ≈2,3 (orquestrador ≈ 1× sozinho) | contexto de 960 k degrada julgamento (Anthropic: "performance degrada quando o contexto enche") | 58 | nunca como padrão |

**Sobre "Opus 5 MAX para tarefas críticas" (pedido do Founder):** não é ruim, e é mais barato do que
parece, porque o custo está em turnos. O risco documentado é outro: em max o modelo faz mais
chamadas, explica mais e amplia escopo. Recomendo **xhigh** como padrão em CRÍTICO e **max** apenas
quando a unidade for de raciocínio (concorrência, algoritmo de reconciliação) — decisão por SPEC, no
card. O A/B (§8) mede os dois.

**Sobre o Fable como executor:** o Fable é o modelo mais capaz e o melhor em corridas longas. Mas o
executor é 85 % do gasto e o Fable custa 2×; a Anthropic mede que Opus 5 chega a 0,5 % do Fable 5
em coding. A inteligência extra do Fable rende mais **onde o Opus não enxerga**: no juiz. E o Fable
tem cota própria no plano (📊 diagnóstico §13.7: "30 % da cota semanal de Opus e 20 % da de
Fable"), então juiz Fable **não compete** com o executor Opus pela mesma janela.

**Sobre este chat:** o Fable continua sendo o co-líder para decidir, auditar e escrever protocolo
(como agora). O que sai é o Fable **acompanhando a execução com 900 k de contexto**.

---

## 4. PROTOCOLO RECOMENDADO — AAA FAST

```
          ┌──────────────────────────── uma SESSÃO NOVA por SPEC · Opus 5 · contexto ≤ 300 k ────────────────────────────┐
          │                                                                                                              │
  PROMPT  │  ① CARD + BLOCO 0        ② BUILD               ③ PROVA MECÂNICA        ④ JUIZ FRESCO         ⑤ CONSERTO     │  ⑥ ENTREGA
  (≤ 6 KB)│  ≤ 15 min                60–90 min             10–15 min               10–15 min             ≤ 25 min       │  ≤ 20 min
  ───────►│  5–10 premissas que      UM escritor,          compile · tsc · guardas  subagente READ-ONLY   o executor     │  push com saída
          │  mudariam o desenho      fatia por fatia,      da superfície · mutação  contexto limpo:       conserta TUDO  │  relatório ≤ 15 KB
          │  (comando ao lado)       commit por fatia      dos guardas NOVOS ·      diff + card + gates   junto, reroda  │  pendências por ID
          │                                                rotas-montam se app/     → até 10 achados      só o afetado   │  suíte inteira em
          │                                                                         com prova                            │  2º plano
          └──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                        ▲ FAIL volta direto ao ②, nunca ao juiz
```

**Quem é quem:**
- **EXECUTOR** = Opus 5 (xhigh em CRÍTICO · high em PADRÃO · medium/high em LEVE). Escreve tudo.
  Pode abrir **no máximo 1 investigador read-only** (Sonnet 5) quando a varredura for realmente
  paralela e grande. Não delega o que faz em poucas chamadas. Não delega verificação do próprio
  trabalho (Anthropic, doc do Opus 5).
- **JUIZ** = subagente fresco, read-only, **Fable 5.1 em CRÍTICO, Opus 5 em PADRÃO, nenhum em LEVE**
  (só provas mecânicas). Recebe: o card, o contrato da SPEC, o diff, os comandos dos gates e a
  lista de ataques fixa (dado vazio · duas corretoras · mesma mensagem 2× · concorrência ·
  rollback · "o produto chama este caminho?"). Não recebe a narrativa do executor. Devolve até 10
  achados, cada um com o TESTE DO PRODUTO (§2 do protocolo) e a medição.
- **NINGUÉM MAIS por padrão.** Aquecimento, desenhista, painel de N lentes, red team separado,
  integrador, auditor externo, pesquisador, juiz de confirmação: só por gatilho (§6).

**O que fica do AAA v11.2, intacto:** §0.2 EXECUTION CARD (encurtado) · §0.3 O ELO · §0.4 a regra do
comando · §2 o teste do produto · §3 as duas contas e o piso · §6 a forma do juiz · §7 a referência
inspecionável · §9 a licença de autonomia e §9.3 "atividade não é progresso" · CLAUDE.md §9.1–§9.5.
**São regras de qualidade, não de custo — e custam zero turno.**

**Fatias:** SPEC grande (≥ 3 unidades ou > 40 KB) roda em **fatias internas** na mesma SPEC e no mesmo
relatório: cada fatia = BUILD → PROVA → commit. O juiz roda **uma vez**, sobre o diff acumulado, no
fim — não por fatia. Se a sessão passar de 300 k de contexto, o executor fecha a fatia verde,
commita, escreve um handoff de ≤ 20 linhas no relatório e a próxima fatia começa em sessão nova.

---

## 5. HARD BUDGETS — e como se aplicam DURANTE a execução

| grandeza | LEVE | PADRÃO | CRÍTICO | CRÍTICO gigante (fatias) |
|---|---|---|---|---|
| relógio alvo | ≤ 40 min | ≤ 75 min | **≤ 2h30** | 2 × 1h15 (mesma SPEC) |
| turnos do executor | ≤ 80 | ≤ 160 | ≤ 250 por fatia | idem |
| contexto do executor | ≤ 200 k | ≤ 250 k | ≤ 300 k | fecha a fatia ao passar |
| agentes além do executor | 0 | 1 (juiz) | 2 (juiz + 1 investigador read-only) | 2 |
| juiz: turnos · contexto | — | ≤ 60 · ≤ 200 k | ≤ 80 · ≤ 250 k | idem |
| rodadas de juiz | 0 | 1 | 1 (+1 confirmação curta só por gatilho §6) | idem |
| custo API-equiv. 💭 alvo | ≤ US$ 12 | ≤ US$ 30 | ≤ US$ 60 | ≤ US$ 45 por fatia |
| documento de entrada | ≤ 25 KB | ≤ 40 KB | ≤ 40 KB (+ apêndice que o executor NÃO lê inteiro) | idem |
| relatório de saída | ≤ 8 KB | ≤ 12 KB | ≤ 15 KB | idem |

**Como se aplica de verdade (nenhum destes é frase de relatório):**

1. **`.claude/settings.json` do projeto** — determinístico, recomendado pela própria Anthropic para o Opus 5:
   ```json
   "env": { "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "2", "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1" }
   ```
2. **Hook `PreToolUse` sobre `Agent`** que conta as chamadas da sessão e **bloqueia a 4ª** (exit 2 com a
   mensagem "teto de agentes do AAA FAST"). Um hook é executado pelo harness, não pelo modelo; não há
   como "esquecer".
3. **Hook `PreToolUse` sobre `Bash` com `pytest`** que filtra a saída para falhas (exemplo oficial da
   Anthropic em `code.claude.com/docs/en/costs`) — corta dezenas de milhares de tokens de contexto por
   rodada.
4. **Status line com contexto** (`/statusline`): o executor tem a regra escrita de conferir o contexto
   em cada gate; passou de 300 k → fecha a fatia. Isso é disciplina de prompt; o item 5 é a rede.
5. **Medição pós-execução obrigatória:** [`AAA-FAST-medir-execucao.py`](AAA-FAST-medir-execucao.py)
   roda sobre a sessão e cola no relatório as 8 linhas (turnos, contexto de pico, ctx-tokens,
   saída, US$, relógio por fase, agentes, achados por mecanismo). **Relatório sem essas linhas =
   SPEC aberta** (mesma regra do card hoje).
6. **Relógio:** o card traz a faixa; ao chegar a **1,5× a faixa** sem blocker aberto, o executor
   para de construir, entrega a fatia verde, registra o resto e **não convoca mais ninguém**. A
   resposta a "estourou" nunca é "mais agentes".

---

## 6. ESCALATION TRIGGERS — quando a execução simples ganha uma peça

| peça | entra quando (qualquer um) | quem decide | custo 📊 medido |
|---|---|---|---|
| **lente do dado** (1 subagente Opus, read-only, reconstrói o outcome sobre o acervo por SELECT) | o outcome é NÚMERO, DATASET ou relatório que a corretora lê · migration que ALTERA DADO · a SPEC afirma percentuais do acervo | executor, no card | 10–34 min · US$ 2–7 (001.6 achou 2 blockers; 001.1 achou 1 que nenhum guarda via) |
| **confirmação pós-conserto** (juiz do mesmo modelo, novo, ≤ 20 turnos, só o diff do conserto) | o juiz achou ≥ 1 BLOCKER em código que ENVIA, filtra `company_id` ou grava por migration | executor | 💭 5–10 min |
| **red team dedicado** (Fable, read-only, missão: quebrar) | autenticação/sessão · cross-tenant · dinheiro/cobrança real · ação irreversível a terceiro (portal, chamado) — **além** da lista de ataques que o juiz já carrega | card (piso §3.2) | 14–63 min · US$ 3–13 |
| **Fable como consultor antes do BUILD** (uma consulta, ≤ 15 turnos) | a SPEC deixa uma decisão de arquitetura em aberto ("não sei onde pega" = SUPERFÍCIE 3 real) | executor | 💭 5–10 min |
| **segundo juiz** (família diferente do primeiro) | o primeiro reprovou com ≥ 2 blockers materiais E a SPEC é de envio/tenant | executor | ≈ o custo do 1º |
| **AAA completo v11.2** (painel 3 lentes + red team + lente + confirmação) | incidente P0/P1 · mudança ampla de arquitetura · migration DESTRUTIVA (DELETE/UPDATE em massa) · o Founder disse "isto é mais importante do que parece" · o juiz reprovou DUAS vezes seguidas com blocker material | Founder, ou o executor com a CAIXA DO FOUNDER | 6–16 h · US$ 75–240 |

⛔ **Nunca entra por gatilho:** aquecimento de 16 perguntas (a SPEC já foi revisada na criação),
conversão de proposta, pesquisador externo (as referências vêm da proposta), integrador (um escritor
só não precisa integrar).

---

## 7. REGRAS ANTI-BLOAT — o que impede o protocolo de voltar a 15 h

1. **Um escritor por SPEC.** Builder A/B/C/D só existe em ESCALAÇÃO escrita. Paralelizar escrita nunca
   comprou relógio aqui (📊 001.1: B → C → D serial por arquivo-hub).
2. **Nenhum orquestrador.** Quem executa é quem escreve. A sessão de execução nasce vazia.
3. **Teto de agentes por hook (3), de concorrência por env (2), de profundidade por env (1).**
4. **Turnos são o orçamento**, não "tokens de subagentes". O script mede; o relatório cola.
5. **Nenhuma peça nova entra no laço padrão sem um blocker exclusivo medido em 2 SPECs** — a regra do
   §13 do protocolo ("achados ÷ custo"), agora com a evidência obrigatória em `PROTOCOLO-AAA-EVIDENCIAS.md`.
6. **Nenhuma rodada além da 1ª sem gatilho** ("More rounds, more noise": +62 % de falsos positivos).
7. **Documento de entrada ≤ 40 KB** e o executor lê **§0 + as unidades**; o resto é apêndice sob demanda.
   Guarda: o prompt-modelo aponta as seções por número.
8. **Relatório ≤ 15 KB em template fixo de 10 seções**; PENDENCIAS/DECISIONS/ADDENDA numa única passada,
   um commit; dossiê republicado **fora** do caminho crítico (Sonnet, depois do push, ou em lote semanal).
9. **Suíte inteira em 2º plano, uma vez, com triagem por diff da linha de base** (a lista das 14–24
   falhas pré-existentes vive num arquivo versionado; só a diferença é triada).
10. **Mutação só nos guardas NOVOS, uma vez, pelo executor.** O juiz reproduz 3 por amostra (§0.4), não
    reroda todas.
11. **Effort não é lever de custo aqui** — não se baixa effort para economizar; baixa-se turno.
12. **O card cabe em 12 linhas.** Se precisar de mais, é SPEC demais para uma fatia.
13. **Quando a regra errar duas vezes, muda o número** e registra em EVIDENCIAS — e a mudança nunca
    acrescenta papel; troca um por outro.

---

## 8. TESTE A/B — as próximas 3 SPECs

**Linha de base (já medida, 📊):** 001.6 · 001.1 · 001.2 sob laço curto — tabela do §2.2 + achados
por mecanismo (001.6: juiz 2 B + lente 2 B; 001.1: juiz 0 B + lente 1 B; 001.2: juiz 2 B + lente 0 B).

| SPEC | marcha | arranjo | o que mede |
|---|---|---|---|
| **EXTRA-001.3** (grupo, envio, migration, 7 unidades) | CRÍTICO em 2 fatias | Opus 5 **xhigh** executor → Fable 5.1 juiz · lente do dado por gatilho (platform_sends é dataset) | o caso duro: FAST aguenta uma SPEC de 109 KB? |
| **EXTRA-001.4** (corredor) | CRÍTICO | Opus 5 **max** executor → Fable 5.1 juiz | max × xhigh: turnos, achados do juiz, nota |
| **EXTRA-001.5 ou 001.7** (PADRÃO) | PADRÃO | Opus 5 high → Opus 5 juiz | o arranjo barato segura PADRÃO? |

**Métricas, todas pelo script + relatório, sem opinião:** relógio total e por fase · turnos e contexto
de pico por agente · ctx-tokens e US$ · nº de agentes · blockers por mecanismo (executor-próprio ·
provas mecânicas · juiz · lente · canário) com a marca **EXCLUSIVO** · regressões achadas na suíte ·
defeitos que chegaram ao canário do Founder (o único juiz que não mente) · nota do executor e do juiz.

**Regra de decisão, escrita antes de rodar:** FAST vira default se, nas 3, (a) custo ≤ 50 % da linha de
base por marcha, (b) relógio ≤ 2h30 em CRÍTICO, (c) defeitos no canário ≤ os da linha de base, (d)
o juiz não reprovou duas vezes. Se (c) falhar em uma SPEC de envio → a lente do dado e a confirmação
pós-conserto entram no padrão CRÍTICO (não o AAA inteiro). Se (a) falhar com (c) ok → o culpado é
turno: baixa-se o teto de turnos, não se sobe o de agentes.

**Controle:** a 001.3 é a única com fatias; se ela custar > 2 × a 001.4 por unidade, o custo é das
fatias (handoff), e a regra de fatia muda.

---

## 9. NOTAS (0–100)

| processo | qualidade | velocidade | custo | risco | chance de terminar a fila | **geral** |
|---|---|---|---|---|---|---|
| AAA completo v11.2 como padrão | 90 | 30 | 25 | 45 | 20 | **48** |
| laço curto como foi projetado (§13.7) | 85 | 65 | 65 | 55 | 60 | **68** |
| laço curto como foi executado (001.6/1/2) 📊 | 85 | 40 | 35 | 45 | 30 | **52** |
| execução tradicional antiga (Opus só, sem juiz) | 70 (LEVE 85 · CRÍTICO 55) | 95 | 95 | 45 | 85 | **74** |
| AAA FAST 1+1 do ChatGPT, como escrito | 88 | 85 | 80 | 65 | 85 | **83** |
| **AAA FAST (esta proposta)** 💭 até o A/B | 90 | 88 | 88 | 65 | 90 | **89** |

Critério de "qualidade": o que chega ao segurado e à corretora sem defeito material, com a evidência
de que o mecanismo acha o que o construtor não vê. "Risco" inclui o risco de o processo não medir
o próprio custo (por isso 65 no FAST até haver 3 SPECs medidas). A nota 89 é **alvo**, não medição;
a primeira marca real sai na 001.3.

**O que o FAST perde, dito com todas as letras:** ~10 % dos achados de borda que só um painel de
lentes diferentes vê (📊 094: 2 achados vistos por 2 frentes ao mesmo tempo; 096: 2 exclusivos da
lente do dado). Em SPEC de dado, a lente volta por gatilho. Em SPEC de envio, o juiz carrega a
lista de ataques do red team. O que não volta: rodada 3, painel homogêneo, aquecimento.

---

## 10. ARQUIVOS PROPOSTOS (nesta pasta, sem tocar o canon)

| arquivo | o que é |
|---|---|
| [`PROTOCOLO-AAA-FAST-PROPOSTA.md`](PROTOCOLO-AAA-FAST-PROPOSTA.md) | o protocolo, 10 KB, no formato do v11.2 (só regras; o porquê está aqui) |
| [`PROMPT-EXECUCAO-AAA-FAST-MODELO.md`](PROMPT-EXECUCAO-AAA-FAST-MODELO.md) | o prompt único de abertura (≤ 6 KB), com o bloco [SPEC] a trocar |
| [`AAA-FAST-medir-execucao.py`](AAA-FAST-medir-execucao.py) | a telemetria que produziu o §2, para colar no relatório de cada SPEC |
| este arquivo | a auditoria e a evidência |

---

## 11. MIGRAÇÃO — o que muda, revoga ou ganha precedência

| documento / decisão | hoje | o que fazer (quando o Founder aprovar) |
|---|---|---|
| `PROTOCOLO-AUTOBROKERS-AAA.md` v11.2 | laço com painel por nível (§3.1), 10 papéis (§4), orquestrador = Fable (§10) | vira **v12 = AAA FAST + modo ESCALAÇÃO**: §3.1 recebe a tabela do FAST; §4 encolhe a executor + juiz + peças de escalação; §5 vira o laço de 6 passos; §10 troca "orquestrador Fable" por "executor Opus em sessão nova" e "orçamento em tokens" por "turnos × contexto"; §11 aponta o script. §0–§2, §3, §6, §7, §9 ficam. |
| `PROTOCOLO-AAA-EVIDENCIAS.md` | — | recebe o §2 desta auditoria (a medição que produziu a v12) |
| `CLAUDE.md` §2 | "TODO pacote a subagente carrega o protocolo §0–§3, §5 e §7.3" · §9 "pasta única AutoBrokers-Opus-Exec" (já vencido) | §2: o pacote é só o do JUIZ; o executor lê o protocolo uma vez. §9: "uma sessão NOVA por SPEC, executor Opus 5; Fable para decidir e auditar". Nada entra no NÚCLEO sem sair outro: o v12 é menor que o v11.2. |
| `FOUNDER-DECISIONS.md` | **D-PILOTO-14** "AAA opção B na execução" · **D-PILOTO-20** "execução em chat novo por SPEC, sob AAA opção B" · §13.7 do diagnóstico "laço curto substitui o AAA completo" | nova **D-PROTO-01 (16/09)**: "AAA FAST é o default de execução; AAA completo é ESCALAÇÃO por gatilho (§6); D-PILOTO-14 e a segunda metade de D-PILOTO-20 ficam superadas; 'chat novo por SPEC' continua". |
| `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §13.7 | opção C laço curto, nota 88, teto 💭 1 M tokens | nota de rodapé: superado por D-PROTO-01; o teto em "tokens" era grandeza errada (§2.1 daqui) |
| `specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.x-MODELO.md` | prompt do laço curto (Fable orquestra, 1–2 builders, teto 1 M) | substituído por `PROMPT-EXECUCAO-AAA-FAST-MODELO.md`; fica com um cabeçalho "SUPERADO em 16/09" |
| prompts individuais 001.3 / 001.4 / 001.5 / 001.10 | "ORQUESTRADOR Fable · AAA v11.2 + OPÇÃO B · investigador, pesquisador, aquecimento, 3 lentes, red team" | **não se executam como estão.** Cabeçalho: "o MODELO FAST prevalece; use daqui só §1 (arquivos), §2 (autorizações) e §3 (estado herdado)". |
| `docs/canon/pacotes/` | 5 pacotes; o guarda exige ≥ 5 | PACOTE-JUIZ ganha a lista de ataques e o modelo por marcha; PACOTE-BUILDER vira o card do executor; AQUECIMENTO, AUDITOR-EXTERNO e PESQUISADOR ganham a linha "só em ESCALAÇÃO". Os 5 arquivos continuam existindo (o guarda passa). |
| `backend/tests/test_o_protocolo_tem_policia.py` | exige EXECUTION CARD (3000 chars) com as linhas de `LINHAS_DO_CARD`, 3 URLs externas em SPEC ≥ 088, núcleo §0–§5 ≤ 11 KB | o card do FAST mantém as mesmas linhas (encurtadas) → passa; as 3 URLs vêm da proposta, não de pesquisa nova → passa; o v12 tem de caber em 11 KB de núcleo → a proposta cabe em 9 KB. **Rodar o guarda antes de promover o v12.** |
| `.claude/settings.json` | só `subagentPromptCacheTtl` | + `env` com os dois tetos + os 2 hooks (§5). ⚠️ hooks são configuração do harness: mudar exige a aprovação explícita do Founder (CLAUDE.md §13.1 vale em espírito). |
| `SPEC-EXECUTION-REPORT-TEMPLATE.md` | 11 KB, seções abertas | versão FAST de 10 seções, ≤ 15 KB de saída, com as 8 linhas de telemetria do script obrigatórias |
| `ESTADO-DAS-SPECS.md` / `EXECUTION-MASTER-PLAN.md` | — | uma linha: "a partir da 001.3, AAA FAST (D-PROTO-01)" |

Ordem sugerida, num só commit de docs: D-PROTO-01 → v12 → CLAUDE.md §2/§9 → MODELO → cabeçalhos dos
prompts individuais → settings/hooks → template → guarda verde → push. 💭 45–60 min de trabalho de
documento, sem subagente.

---

## 12. RECOMENDAÇÃO FINAL AO FOUNDER

1. Os relatórios exageraram o relógio (fuso) e mediram "tokens" errado (contexto final, não consumo).
2. Mesmo corrigido, o problema é real: 5–9 h e ≈US$ 80–205 de API-equivalente por SPEC, mais o orquestrador.
3. O laço curto cortou o que era barato (painel) e manteve o que era caro (orquestrador de 900 k, agentes de 350+ turnos, fechamento de 1h+, propostas de 100 KB).
4. O juiz fresco é o melhor dinheiro gasto no laço inteiro: 11 min, US$ 3, dois blockers reais na 001.2.
5. Amanhã, na EXTRA-001.3, eu usaria o **AAA FAST**: sessão nova, Opus 5 xhigh executando sozinho em duas fatias, um juiz Fable 5.1 fresco no fim, um conserto, push.
6. Lente do dado entra nela por gatilho (o outcome é dataset de envios); red team separado não entra; AAA completo não entra.
7. Os tetos passam a ser turnos e contexto, aplicados por env e hook do Claude Code, e medidos pelo script no relatório.
8. Este chat (Fable) continua sendo onde decidimos e auditamos; ele deixa de acompanhar cada SPEC turno a turno.
9. Espere 2h–2h30 e cerca de 1/3 do custo medido na 001.2, com a mesma qualidade (88–92). Não espere 98.
10. Se a 001.3 quebrar o alvo, a resposta é baixar turno e cortar documento, nunca acrescentar agente.
11. Antes de rodar: aprovar D-PROTO-01, promover o v12 e o prompt-modelo, e aprovar os hooks. 45–60 min de documento.
12. Nada disto está no canon ainda; está tudo nesta pasta e num commit local de proposta.

---

## 13. Fontes

**Internas (📊):** transcritos `a4546c6b` (001.6/001.1/001.2), `584e515a` (pilotos + criação das
propostas), `ed17368c` (095–097.1), `5ee209a7` (098), `1ad9b0a0` (EXTRA-001) · `git log` 13–15/09 ·
`reports/SPEC-EXTRA-001.{1,2,6}-EXECUTION-REPORT.md` · `reports/SPEC-09{4,4.1,5,6,7,7.1,8}-EXECUTION-REPORT.md`
· `PROTOCOLO-AAA-EVIDENCIAS.md` · `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §13 ·
`FOUNDER-DECISIONS.md` D-PILOTO-14/20 · `backend/tests/test_o_protocolo_tem_policia.py` · `.claude/settings.json`.

**Externas (lidas em 16/09/2026):**
- Anthropic, *Prompting Claude Opus 5* — platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5 (delegação, over-verification, review precision/recall)
- Anthropic, *Effort* — platform.claude.com/docs/en/build-with-claude/effort (recomendações por modelo; max = "custo significativo por ganho pequeno")
- Anthropic, *Optimizing for cost and intelligence* — platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence (Opus 5 + Fable 5.1 advisor: +3,5 pts; Fable+Fable: "quase nada")
- Anthropic, *Advisor tool* — platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool
- Anthropic, *Introducing Claude Opus 5* — anthropic.com/news/claude-opus-5 (CursorBench: 0,5 % do Fable 5 por metade do custo)
- Anthropic, *Claude Code best practices* — code.claude.com/docs/en/best-practices (Writer/Reviewer; "fresh context improves review"; adversarial review step; subagentes para investigação)
- Anthropic, *Manage costs* — code.claude.com/docs/en/costs (contexto reenviado a cada turno; hook que filtra pytest; "long context" como causa nº 1)
- Anthropic, *Subagents* — code.claude.com/docs/en/sub-agents (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, `..._SPAWN_DEPTH`)
- Cognition, *Multi-Agents: What's Actually Working* (22/04/2026) — cognition.com/blog/multi-agents-working
- Kohli, *Nine Judges, Two Effective Votes* — arxiv.org/abs/2605.29800
- *More Rounds, More Noise: Why Multi-Turn Review Fails* — arxiv.org/abs/2603.16244
- Böckeler/Fowler, *Harness engineering for coding agent users* (02/04/2026) — martinfowler.com/articles/harness-engineering.html
- rulestack, *We said a subagent costs 436k tokens; a cleaner measurement says 54k* — dev.to (a mesma confusão contexto × consumo)
