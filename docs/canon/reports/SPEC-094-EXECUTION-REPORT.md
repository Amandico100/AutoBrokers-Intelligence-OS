# SPEC-094 · O PULSO 360 NÃO PERTENCE À INFOCAP — relatório de execução

> **v2.1 da SPEC, executada sob o protocolo v11.1 → v11.2 · nível CRÍTICO** · 03/09/2026 · branch
> `feat/spec094-o-pulso-360-nao-pertence-a-infocap` · commit inicial `b036b18` · commit final de código `8019322`
> Orquestrador: Fable 5.1. Subagentes Opus 5: investigador · aquecimento · censista · desenhista (2, um morto por 429) ·
> builders (0-bis+H · A→D · E→G) · painel: L1 verdade/ELO/regressão/tenant · L2 lente do DADO · red team · builder do conserto · juiz fresco (confirma + audita) · canário vivo

## 0.1 EXECUTION CARD — como foi

```
SPEC .................  094 · O Pulso 360 não pertence à InfoCap
OUTCOME ..............  o dono pergunta "como estamos?" e recebe números com ponteiro (metric_id@versão · base temporal · cobertura),
                        calculados uma vez sobre fatos canônicos; a InfoCap é um adapter; ausente sai UNAVAILABLE, nunca zero
PISO .................  §3.2 atingido: credencial de 3 tenants no caminho + leitura cruzada (conta compartilhada) → CRÍTICO por piso
TIME .................  Fable orquestra · Opus: investigador, aquecimento, censista, desenhista, 3 builders, 2 lentes, red team, juiz fresco,
                        2 builders de conserto · Sonnet: nenhum (a confirmação mecânica foi a suíte)
REFERÊNCIA ...........  6 externas reabertas em 03/09 (ACL Microsoft/AWS · dbt Semantic Models + time spine · Cube · Claude Citations) +
                        internas: policy_data_provider.py (padrão de registry), infocap_connector.py (resolver), templates.py (CATALOGO)
GATES ................  por bloco (A 24 · B 39 · C 27 · D 32 · E 18 · F 13 · G 18) + guarda 284 + canário 115 + 3 scripts npm + suíte 933/6 + canário VIVO
RISCO ................  7  (número executivo lido pelo dono · tool viva nas 3 corretoras · credencial de 3 tenants) — confirmado
SUPERFÍCIE ...........  3  — confirmado; +1 arquivo que a §4 não listava (`test_a_fonte_comercial…` com nome de produtor)
NÍVEL ................  CRÍTICO — desenhista antes do código · painel 2 lentes (verdade+regressão+tenant · DADO) · red team · juiz fresco (confirma + audita) · integrador
UNIDADES .............  10  BLOCO 0 · 0-bis · H · A · B · C · D · E · F · G — todas entregues
COESÃO ...............  0 ‖ (0-bis+H) ‖ desenhista · A→B→C→D serial (um builder) · E→F→G serial (um builder)
PARALELISMO REAL .....  3 no início (censo · ELO · guarda) · 1 depois
O ELO ................  MEDIDO: conexão da Resulta → adapter → CBIM → registry → MetricResult; provider de referência dá o MESMO
                        envelope para 16 métricas (M17); a string das duas tools da 081 não tem número em prosa; Artifact lê o mesmo pack_id
GATE ZERO ............  os 4 VERMELHOS em HEAD antes do código (prosa com número e nome · _num(None)==0 · nosnum em calculos · nome de
                        produtor no teste), provados pelo guarda do desenhista; VERDES depois
FAIXA DE RELÓGIO .....  declarada 14–18h · 📊 realizada: conversão 09:00→09:40 (0h40) + censo 09:43→10:02 · execução 10:20→~20:45 em 3 janelas (2 mortes de janela: ~10:40 e ~17:00; ≈ 9h de trabalho efetivo) — dentro da faixa de relógio, fora da meta de uma janela
ORÇAMENTO ............  ≤ 2,5 M tokens de subagentes · 📊 gasto: investigador 154k · aquecimento 153k · censista 203k · desenhista 226k
                        (+ metade herdada do morto) · A→D 481k · investigador interno 175k · pesquisador externo 236k · E→G 411k ·
                        painel L1 127k · L2 195k · red team 225k = 547k · TOTAL ≈ 3,4 M (com conserto 375k + 238k e juiz fresco 198k) — ACIMA do orçamento de 2,5 M; sem as pesquisas da 094.1 (411k) ≈ 3,0 M
BATERIA ..............  suíte inteira 3× (a do gate D contaminada pelo bloqueio de rede do guarda — ver §5); scripts comerciais a cada bloco
```

```
o painel rodou sobre CÓDIGO?          sim: 2 lentes fundidas + red team (v11.2), contexto limpo, sobre o diff b036b18..2ea6df8, depois dos gates de bloco
conserto criou defeito?               sim, UM: o conserto da rota vazia fechou uma direção e deixou o espelho (renovações vazia → 0 HIGH) — pego pelo juiz fresco, consertado com ROTA PRIMÁRIA na 2ª rodada. E o juiz fresco achou o maior defeito da SPEC, que nenhum guarda via: a tool NÃO RODAVA no grafo (Supabase síncrono × resolver assíncrono) — 366 asserções verdes com fakes que respondiam a `await`
o que sobrou é MATERIAL?              não: seed da migration a aplicar (ação do Founder), custo de 10 GET/≈80 s por pergunta (P-094-CUSTO-API), um Artifact por pergunta não-cacheada (P-094-ARTIFACT-POR-PERGUNTA), cobertura 80,6% de 2025 não reproduzida ao vivo (medida 2026: 87%)
```

## 0.2 A TELEMETRIA (§11)

```
começou / terminou                     03/09 09:00 (investigador) / 03/09 ~20:45 (push)
tempo até a PRIMEIRA linha de código   📊 1h20 (09:00 → 10:20, commit 6ecb50d do 0-bis) — inclui investigação, 6 referências, SPEC v2, aquecimento e censo
rodadas de painel e achados por lente  L1 2 blockers + 6 pend · L2 (dado) 2 blockers + 6 pend · red team 7 quebras + 4 pend. Únicos: 12 blockers de produto/guarda; 2 achados por 2 frentes (cobertura no Artifact; vocabulário)
defeitos que o painel NÃO pegou        o bloqueio de rede do guarda derrubando 99 testes (orquestrador, comparando com a linha de base da 093-B); a tool não rodar no grafo (juiz fresco no canário VIVO — painel e guardas usavam fakes que respondiam a `await`); o fingerprint com separador errado (o builder de E/F/G, no canário em memória)
rodadas da bateria                     📊 diário do conftest 03/09: suíte inteira 3× (gate D 831/99 — contaminada pelo bloqueio de rede na coleta; diagnóstico 933/4; final 933 passed · 6 failed (20:40→20:55, 14m05, árvore parada) — os 6 passam isolados: 093-B 249 ok · ferramentas 38 · política 1 passed · ontologia 1 passed · todo_import verde · árvore-limpa = harness (P-093B-HARNESS: guardas-script se atropelam; um crash de libuv do node num subprocesso)); parciais ~90 (guarda 259→284, canário 107→115, 3 scripts npm a cada bloco)
nota 0–100 do orquestrador             84/100 — 10 unidades entregues, 16 métricas com paridade ao centavo por dois caminhos e pela API viva, 16 blockers do laço fechados e provados por mutação, zero linha mudada no atendimento; perde por ter chegado ao juiz fresco com a tool que não rodava no grafo, por estourar o orçamento de tokens (≈3,0 M × 2,5 M) e por 80 s/10 GET por pergunta
```

## 1. O que a SPEC prometeu e o que ficou

**Antes:** a 081 entregava duas tools de chat sem tela; 📊 28 relatórios na Resulta, todos de 18/08, zero na Amandus e na AutoFleet.
A matemática "pura" usava `nosnum` (7×); o provider resolvia pelo NOME da corretora; `_num(None)` → 0,0; o número chegava ao modelo
como prosa com nome de produtor; o canon tinha duas verdades sobre o 403 da CorpAPI e 18 rotas "a liberar".

**Depois:** a InfoCap é um adapter atrás de um port permanente; 16 métricas versionadas com base temporal num registry que não conhece provider (M1 vermelho por mutação); ausente sai UNAVAILABLE em três lugares (envelope, bloco do modelo, Artifact); o número chega ao modelo como bloco citável com `pack_id`, e o Artifact `executive.pulse360` lê o mesmo pack; comparação atual × anterior no bloco (12), com recusa de janelas desiguais; manifesto de capacidade fail-closed com drift por fingerprint; conexão por `tenant_connections` (status connected) com gate de conta compartilhada — a Amandus é recusada em 1,1 s porque é a conta da Resulta; censo machine-usable com 51 rotas; provider de referência prova que a matemática não muda de provider. 📊 Canário vivo: Resulta 972 apólices · R$ 1.472.165,72 · cobertura de produtor 87% (2026 até 03/09) · AutoFleet 2.300 · R$ 1.746.002,17 · Amandus recusada · 2 Artifacts publicados

## 2. As unidades, uma a uma

| bloco | commit | o que fez | gate |
|---|---|---|---|
| 0 · censo | `8ad7083` | 86 GET pelas 3 conexões (descriptografia pelo caminho do produto); 5 arquivos machine-usable em `docs/canon/providers/infocap/`; MAPA antigo superado | manifesto com 51 rotas × classe · zero PII (grep) · golden controls por corretora |
| 0-bis · ELO | `6ecb50d` | as duas tools devolvem `EvidencePack.bloco_para_o_modelo()`; Artifact lê o mesmo `pack_id`; sem número em prosa, sem nome | `test:ferramentas-comerciais` 31 · `test:fonte-comercial` 26 · mutação "liderado por {nome}" vermelha |
| H · higiene | `81859d4` | nome de produtor real sai do teste versionado; controle vira razão sem identidade | grep de nomes → 0; 26 verdes |
| A · CBIM | `1801d72` | fatos canônicos, `Money`/`UNAVAILABLE`, `Provenance` com `account_fingerprint`, `policy_ref` por corretora | 24/0; mutação UNAVAILABLE→None vermelha |
| B · port + adapter | `1e5929f` | `BrokerageAnalyticsProvider` (mesmo padrão de `policy_data_provider`); adapter InfoCap sobre `_resolve_infocap_connection`, `status='connected'`, gate de conta compartilhada, cache com `company_id+connection_id`, `UPDATE last_used_at` | 39/0; M11 vermelha; conta compartilhada recusa |
| C · manifesto | `992bedf` | estados SUPPORTED/PARTIAL/UNAVAILABLE/UNKNOWN/DEGRADED do JSON do censo; drift por fingerprint bloqueia só a métrica dependente | 27/0; M2/M14/M15 vermelhas |
| D · registry | `d9cd31b` `ed7a70f` | 16 métricas migradas das 11 funções (`nosnum`→`policy_ref`), `time_basis` obrigatório, `comparar` recusa bases distintas; `repasse` soma TODOS os `prod_docs`; `contribution` DERIVED na interseção | 32/0; paridade adapter × referência exata; M1/M5/M6 vermelhas; `test:calculos-comerciais` 81 |
| E · pack + sinal | `a468f7c` | findings determinísticos no pack; 3 viram `commercial_opportunity` com evidência (`SignalDraft.valido()` real); cobertura baixa fica no pack | guarda [7] 18/18; M16 vermelha |
| F · tool + wrappers | `a67a538` `c855861` `ff7ad4f` | tool `executive_intelligence` (query plan, default YTD × ano anterior, follow-up por pack_id), wrappers da 081 sobre o registry, mapa de produtor (`producer-roles.{slug}.json`, default unknown), fix do fingerprint `,`→`|` e do ruído de float | guarda [8] 13/13; M3/M7/M8 vermelhas; `test:ferramentas-comerciais` 37 |
| G · template + seed + canário | `a982fc7` `2ea6df8` | template `executive.pulse360` (8 seções) + migration de SEED `20260903_01_spec094_seed_template_pulse360.sql` (ON CONFLICT, APPLY/VERIFY/ROLLBACK) + provider de referência no guarda + canário em memória para as 3 corretoras | guarda [9] 9/9 · [10] 9/9; canário 99 verdes; Amandus recusada |

## 3. 📊 Os números

```
paridade (fixture sintética, dois caminhos)    1.680 apólices · R$ 1.863.830,79 comissão · R$ 11.910.456,05 prêmio · 3.536 vencimentos · 97 produtores · 717/963
golden controls REAIS (censo, 2025)            Resulta 1.680 · R$ 1.863.830,79 · 3.536 · 97 · 97,1% ordem 1 · BI∩renov 100
                                               AutoFleet 3.117 · R$ 2.099.510,43 · 2.654 · 64 · 99,1% · BI∩renov 0
                                               Amandus = Resulta ao centavo (P1)
val_r = val_c × per_r / 100                    198/198 linhas, desvio máximo R$ 0,01
rotas CorpAPI                                  15 classe 200 · 1 × 400 · 1 × 500 · 34 × 403-SigV4 (não existem) · flags do perfil 17/17 = T
latência                                       /renovacoes 90 d 2,28 s · /documentos_bi 1 ano 3,3–7,5 s · Raio-X anual ≈ 45–60 s
guarda da SPEC                                 284 ok · 0 falhas (era 130 → 199 → 259 → 284) · canário 115 verdes
grep M1 (provider dentro da fórmula)           0 em comercial/metricas · 0 em calculos.py · 2 em agents/tools (infocap_tool.py, SPEC-016, fora da §4)
```

## 4. O aquecimento e o censo mudaram a SPEC — antes do código

Aquecimento (Opus, 16 perguntas, nota 74 → v2): refutou meu 📊 do "Radar 8 s" (existia em `fonte_infocap.py:168`);
achou o resolver por conexão já existente; mostrou que o Fabric recusa `domain` gravável e exige evidência; que o guarda de
templates exige seed SQL (a promessa "zero migration" caiu para "uma seed"); um nome de produtor real num teste versionado
(BLOCKER → BLOCO H); a tool nova aparece para as 3 corretoras (intencional, escrito). 15 emendas aplicadas.
Censo (v2.1): 18 rotas "negadas" não existem; `/sinistros` existe (5.729); `val_r` provado; `ordem==1` não é o maior repasse;
AutoFleet BI∩renov = 0; **P1 Amandus = Resulta** (F-094-07).

## 5. O laço

Três frentes Opus 5 (v11.2: 3 lentes → aqui 2 lentes fundidas + red team), contexto limpo, sem o relatório dos builders, sobre o diff
`b036b18..2ea6df8`, cada uma rodando os guardas e mutando por cópia. **📊 Custo: L1 127k · L2 195k · red team 225k tokens** (a v11.1
gastou ≈900k em 4 lentes + red team na 093-B).

| frente | veredito | nota | o que achou de único |
|---|---|---|---|
| verdade + ELO + regressão + tenant | PASS c/ pend. | 82 | Produto bom: ELO em processo ponta a ponta; tenant e cache isolados; migration expand-only com o melhor rollback da leva; **zero linhas** mudadas em api/dispatch/graph. Blockers no GUARDA: 20 asserções verdes ainda em `vermelho_ate` (uma regressão real do ELO saía como "+0 de verdade" — provado com M10); gate M1 inalcançável (87 linhas pré-existentes de tools de atendimento no escopo) |
| a LENTE DO DADO (6 GET vivos na Resulta) | PASS c/ pend. | 76 | **Os 4 números recalculados à mão direto da InfoCap batem ao centavo** com o registry e o censo (1.680 · R$ 1.863.830,79 · 3.542 · R$ 599.594,82 — repasse de TODOS os prod_docs 36% acima do só-ordem-1). Blockers: o Artifact escreve "sobraram R$ 98 mil" sem a cobertura de 6% ao lado (a ressalva mora 6 seções depois); o canário prova cobertura de produtor sobre uma fixture que ignora `dt_ini/dt_fim` (crava 5,95%; o produto entrega ≥ 79,5% na API viva — CLAUDE.md §9.4) |
| red team (16 ataques) | 7 quebras | conf. 72 | janelas desiguais comparadas → "+301%" sem aviso; rota vazia → 0 com coverage 1.0 e HIGH; `"NaN"` da fonte → "R$ nan" na manchete; follow-up ignora o período pedido; injeção pelo `dimension` DENTRO do bloco citável; censo corrompido libera tudo (fail-open); a tabela de produtores do Artifact é uma coluna de hashes. Resistiram: mixing de base temporal, cache entre corretoras, `archived`, legado sem credencial, seed/template, PII no chat |

**Fundido pelo TESTE DO PRODUTO (§2): 12 blockers únicos + 8 pequenos, consertados JUNTOS numa rodada (1 builder):**
grupo 1 (o dono lê errado): janelas desiguais · rota vazia ≠ 0 · NaN/Infinity → UNAVAILABLE · follow-up com período · `dimension` em lista
fechada + período absurdo recusado · censo fail-closed · cobertura DENTRO do cartão + `producer_label` só no Artifact · DERIVED declara as duas bases;
grupo 2 (o guarda): `vermelho_ate` → `certo` (20) · escopo do M1 com allowlist · fixture por ano e paridade 80,6% · vocabulário sobre o pack serializado;
grupo 3: normalização de `producer_ref` · fingerprint pela união das chaves · estorno > comissão com aviso · Decimal · PII em 2 testes · gate zero (ii)
na fronteira · baseline do guarda de git-diff · log da conta compartilhada.
**Sobreposição entre frentes:** cobertura/coverage (L2 + red team), vocabulário (red team achou a mutação verde; L1 não olhou), fixture da
cobertura (só L2). **1ª rodada (`4ec66d9` `3221945` `727b6f2`):** 20 itens, guarda 199→259, canário 99→107; o próprio guarda novo achou 2 defeitos nos consertos (âncora dupla do `producer_ref`; frase do fail-closed acusando a fonte). **Juiz fresco (v11.2 §6.1, confirma + audita + canário vivo, 16 GET): FAIL 62** — o conserto criou 1 defeito (espelho da rota vazia) e o canário vivo achou o que nenhum guarda via: **a tool não rodava no grafo** (`AttributeError`); comparações fora do bloco citável; `last_used_at` em hora local. **2ª rodada (7 commits até `8019322`):** os 4 fechados com PAR e mutação; prova viva pelo caminho do grafo (81 s, 972 · R$ 1.472.165,72 · 12 comparações); P2/P3/P5 feitos; P4 registrada (pack_id é uuid por montagem — a chave real é decisão de produto).

### Juiz fresco — confirmação + auditoria do dado (v11.2 §6.1)
Ver §5 acima: FAIL 62 → 2ª rodada → 5 guardas verdes (284 · 115 · 38 · 26 · 81). A confirmação MECÂNICA (v11.2) foi a suíte inteira com a árvore parada, que reroda os dois guardas com as mutações: 933 passed · 6 failed (20:40→20:55, 14m05, árvore parada) — os 6 passam isolados: 093-B 249 ok · ferramentas 38 · política 1 passed · ontologia 1 passed · todo_import verde · árvore-limpa = harness (P-093B-HARNESS: guardas-script se atropelam; um crash de libuv do node num subprocesso).

### O que a bateria mostrou — e o defeito que a própria bateria tinha
📊 A suíte no gate D deu **831 passed · 99 failed · 7 errors**, contra 934/2 no fim da 093-B. O builder atribuiu ao ambiente.
Medido: o guarda novo instalava `socket.connect = _proibir` **no nível do módulo** — o pytest o importava na COLETA e 99 testes de
outros arquivos que falam com o Supabase ficavam vermelhos até o guarda rodar e devolver a rede. Conserto `22021df`: o bloqueio
entra quando o guarda RODA e sai no `finally`. 📊 Suíte depois do conserto (14:52→15:07, 14m18): **933 passed · 4 failed** —
o guarda da 094 (vermelho por desenho até E/F/G), o guarda da 093-B (📊 249 ok isolado: contaminação do builder E/F/G editando
durante a rodada) e os 2 do harness (P-093B-HARNESS). Os 99 eram o bloqueio de rede, não o ambiente. **Lição para o
protocolo:** "o ambiente" nunca é diagnóstico; quem afirma pré-existência mostra a linha de base rodada no mesmo minuto.

## 6. O que ficou pendente (PENDENCIAS.md, com dono)

```
P-094-CONTA-COMPARTILHADA  🧑 P1 · Amandus e Resulta na mesma conta CorpAPI — o adapter recusa a segunda; canário da Amandus não roda
P-094-SINISTROS            🤖 /sinistros com 5.729 registros e nenhum leitor → SPEC-094.1 BLOCO A
P-094-PRODUCAO-500         🤖 parâmetro errado (dt_ini/dt_fim); rota do conector de ATENDIMENTO → fora por trava até o piloto
P-094-RAG-MAPA             🤖 o MAPA errado está no RAG global
P-094-COBERTURA-POR-CORRETORA 🤖 a receita da 081 não vale para a AutoFleet — remedida por corretora no D
P-094-GIT-PII              🧑 nome de produtor no histórico do git
P-094-NUM-PTBR             🤖 `fonte_infocap._num("1.299,09")` → 0,0 (recusa a forma pt-BR); o adapter não a usa para dinheiro; a 081 legada sim
P-094-LEGADO               🤖 resolver por nome atrás de `COMERCIAL_RESOLVER_LEGADO`
P-094-ARTIFACT-POR-PERGUNTA 🤖 toda pergunta não-cacheada publica um Artifact novo (pack_id é uuid por montagem; a chave é (corretora, período, frescor) — decisão de produto)
P-094-SEED-NAO-APLICADO   🧑 a migration de seed existe e não foi aplicada em produção (report_templates = 0 linhas) — F-094-04
P-094-DECIMAL-NAS-FORMULAS 🤖 o registry soma em float (salvo pela serialização a 2 casas); somar em Decimal exige reescrever calculos.py, que a 081 usa
P-094-SEED-023            🤖 `financial.billing_collection` (SPEC-023) nunca foi semeado — pré-existente, fora desta SPEC
```

## 7. Gate da SPEC

```
GATE ZERO ......... ✅ 4 VERMELHOS em b036b18 (reproduzidos pelo juiz L1 com git show); VERDES em HEAD
GUARDA DA SPEC .... ✅ backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py → 284 ok · 0 falhas · canário 115 verdes
PARIDADE .......... ✅ adapter × referência idênticos (16 métricas); à mão × registry × censo ao centavo (lente do dado, 6 GET)
TENANT ............ ✅ company_id em todo SELECT/UPDATE novo; cache por company_id+connection_id; conta compartilhada recusa (Amandus, 1,1 s)
PAINEL ............ ✅ 2 lentes + red team → 12 blockers → rodada 1 → juiz fresco FAIL 62 (4 blockers, 1 criado) → rodada 2 → verdes
CANÁRIO VIVO ...... ✅ Resulta e AutoFleet publicados (artifacts = 1 cada, ready); Amandus recusada; last_used_at deixou de ser NULL nas duas
REGRESSÃO ......... ✅ git diff em api/dispatch/graph = 0 bytes · 81 · 26 · 38 verdes · linha de base da 081 preservada (renomeação pura)
MIGRATION ......... ✅ seed idempotente com APPLY/VERIFY/ROLLBACK escritos · ⚠️ NÃO aplicada (F-094-04)
SUÍTE INTEIRA ..... 933 passed · 6 failed (20:40→20:55, 14m05, árvore parada) — os 6 passam isolados: 093-B 249 ok · ferramentas 38 · política 1 passed · ontologia 1 passed · todo_import verde · árvore-limpa = harness (P-093B-HARNESS: guardas-script se atropelam; um crash de libuv do node num subprocesso)
ENTREGA ........... 03/09 ~21:00 — `git push origin HEAD:main`:
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   6750690..8019322  HEAD -> main
```
```
**Veredito do orquestrador: GATE VERDE — SPEC-094 CONCLUÍDA**, com a migration de seed a aplicar pelo Founder e as pendências da §6.

## 8. 🧑 A caixa do Founder

```
F-094-01  Censo e canário usaram as CONEXÕES (3 connected) pelo caminho do produto; nenhuma CORP_INFOCAP_* entrou em .env.
F-094-02  RESOLVIDA pelo censo: contribuição pós-repasse ENTROU (val_r provado).
F-094-03  A tool nova aparece para as TRÊS corretoras no mesmo deploy. Intencional.
F-094-04  Deploy: `git push origin HEAD:main` + Implantar smith-api + APLICAR a migration de seed `backend/supabase/migrations/20260903_01_spec094_seed_template_pulse360.sql` (APPLY/VERIFY/ROLLBACK no arquivo). Sem smith-web.
F-094-05  Nome de produtor real no HISTÓRICO do git desde a 081 — reescrever histórico é decisão sua.
F-094-06  Rotação das chaves coladas no chat (inclui CORP_INFOCAP_*).
F-094-07  🔴 P1 Amandus = Resulta na CorpAPI (FOUNDER-DECISIONS). Até decidir: recusa.
F-094-08  InfoCap → Agger/Quiver são a mesma casa (FOUNDER-DECISIONS).
F-094-09  Escrita no InfoCap: 5 portas, nenhuma medida (FOUNDER-DECISIONS).
F-094-10  01/10/2026: WhatsApp de serviço deixa de ser grátis.
F-094-11  Custo por pergunta: 10 GET e ≈80 s (a InfoCap, não o modelo). Reduzir exige snapshot (P-094-SNAPSHOT) — decisão de produto/infra.
```

## 9. Riscos remanescentes
- Um push da branch levou 0-bis, censo e H para a `main` sem gate final (CHANGE-ADDENDA 03/09). O gate final desta SPEC os cobre agora.
- `producer-roles.{slug}.json` nasce vazio: todo produtor é "papel não mapeado" até curadoria (P-094-MAPA-PRODUTOR).
- Nenhum motor paralelo: o adapter envolve `FonteInfocap`; o resolver é o do conector; o Artifact é o `ArtifactService`; o sinal é o `SignalService`; a Central não mudou.
- O orçamento de tokens estourou (≈3,0 M × 2,5 M) e duas janelas morreram: o custo do processo está em `DECISAO-DO-RITMO-03-09-2026.md`.

## 📊 A BATERIA — quantas vezes rodou nesta SPEC
📊 conftest 03/09: inteiras 3 (gate D 831/99 contaminada; diagnóstico 933/4 em 14m18; final 933 passed · 6 failed (20:40→20:55, 14m05, árvore parada) — os 6 passam isolados: 093-B 249 ok · ferramentas 38 · política 1 passed · ontologia 1 passed · todo_import verde · árvore-limpa = harness (P-093B-HARNESS: guardas-script se atropelam; um crash de libuv do node num subprocesso)); parciais ≈90. Minutos esperando bateria inteira: ≈45. Lição: a suíte só vale com a árvore PARADA — e um guarda que muda o processo (socket) muda-o quando roda, nunca ao ser importado.
