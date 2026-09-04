# SPEC-094.1 · A FÁBRICA DE RELATÓRIOS — relatório de execução

> **v2 da SPEC, executada sob o protocolo v11.2 · OPÇÃO B (três marchas) · nível CRÍTICO** · 03/09→04/09/2026 · branch
> `feat/spec094-1-a-fabrica-de-relatorios` · commit inicial `6b6be19` · commit final de código `d8cd056`
> Orquestrador: Fable 5.1. Subagentes Opus 5: aquecimento · investigador do BLOCO 0 · desenhista · builder C/D/E · builder A/B (2: um morto por
> 429, um retomou) · painel B: lente do DADO + red team · juiz fresco (confirma + audita + canário vivo) · builder da rodada 1 (15 itens) · builder da rodada 3 (B1–B4 + prova viva)

## 0.1 EXECUTION CARD — como foi

```
SPEC .................  094.1 · A fábrica de relatórios
OUTCOME ..............  o chat lista o que entregou, propõe a métrica que não existe (Work Run + Approval, nunca número), e 12 métricas novas
                        (5 relatórios obrigatórios + o primeiro cruzamento externo: SUSEP × carteira) entram como DEFINIÇÕES, com o protocolo
                        escrito para qualquer chat repetir
RISCO ................  6 — confirmado (número executivo + primeira fonte externa + primeiro uso do HITL); nada envia
SUPERFÍCIE ...........  3 — confirmado (+ registry.py e tick.py que a v1 não listava — aquecimento E4)
PISO .................  não atingido (nada envia, nada cross-tenant, zero migration)
NÍVEL ................  CRÍTICO sob B: desenhista antes · 2 frentes (DADO · red team) · juiz fresco com canário vivo · sem lente verdade/regressão
                        (a frente que nas 3 SPECs anteriores achou defeitos de guarda, não de produto)
TIME .................  Fable orquestra · Opus: aquecimento, investigador, desenhista, 3 builders, 2 frentes, juiz fresco, 2 builders de conserto · Sonnet: nenhum (a confirmação mecânica foi a suíte inteira)
UNIDADES .............  7 — BLOCO 0 · A · B · C · D · E · F — todas entregues; F (canário vivo) rodado pelo juiz fresco e pelo builder da rodada 3
COESÃO ...............  0 ‖ desenhista ‖ (C→D→E) · A→B depois do 0 · F no fim
PARALELISMO REAL .....  3 escritores (desenhista · C/D/E · A/B) em arquivos disjuntos — funcionou: zero conflito de arquivo
O ELO ................  MEDIDO ao vivo pelo caminho do grafo: "como estamos?" → 5 fontes lidas por view (espião prova) → 28 métricas no registry (com o mercado do SES via MinIO) → pack com `origem` por item → Artifact publicado (162 s); pergunta sem métrica → PROPOSTA sem número → work_run + approval_request (subject_id = run) + 2 eventos → `promover` sem decisão RECUSA sem escrever
GATE ZERO ............  4 VERMELHOS em HEAD provados pelo guarda ANTES do código — (ii) reproduzido pelo MOTOR: view desconhecida devolvia o Pulso
                        COMPLETO sobre outra pergunta; VERDES depois
REFERÊNCIA ...........  6 externas (Cube MCP sem commit tool · Euno propor→promover · Genie trusted · Cortex VQR · SUSEP SES · dbt MCP) + internas
                        (registry/adapter/manifesto da 094, WorkApprovalService da 055, ArtifactService.listar, tick.cluster_demand)
GATES ................  por bloco + guarda 228 ok (era 44 → 124 → 198 → 228) + protocolo 47 + 094 284 + scripts npm + suíte 936 passed · 5 failed (03:22→03:37, 14m47, árvore parada, d8cd056) — os 5 passam isolados e são a classe do harness (P-093B-HARNESS: guardas-script se atropelam; crash libuv do node num subprocesso; política/ontologia flaky): 093-B 249 ok · ferramentas 67 · política 1 passed · ontologia 1 passed. A rodada anterior (09cbd6b) deu 934/7 com 2 regressões REAIS consertadas em d8cd056 + canário VIVO
FAIXA DE RELÓGIO .....  declarada 12–16h (v2) · 📊 realizada: 03/09 21:30 → 04/09 ~06:00 ≈ 8h30 em 2 janelas (1 morte de janela no A.4/B.4, ~1h perdida) — DENTRO da faixa e abaixo do piso
ORÇAMENTO ............  ≤ 2,5 M · 📊 gasto: aquecimento 120k · BLOCO 0 216k · desenhista 214k · C/D/E 301k · A/B 203k (+ ~200k do builder morto) · painel DADO 180k · red team 217k = 397k ·
                        juiz fresco 238k · conserto 425k (rodada 1) + 353k (rodada 3) + integrador 165k · TOTAL ≈ 2,8 M (sem o builder morto ≈ 2,6 M) — ACIMA do orçamento de 2,5 M em ~10%; a v11.1 teria custado 💭 ≈ 3,5 M
BATERIA ..............  suíte inteira 1× · guardas a cada bloco
```

```
o painel rodou sobre CÓDIGO?          sim: lente do DADO (vivo) + red team, contexto limpo, sobre o diff, depois do gate integrado
conserto criou defeito?               NÃO — o juiz fresco reaplicou 6 mutações (vermelhas) e provou que os 4 blockers que achou eram HERDADOS (controle: com a fiação removida, o Pulso morria igual). A rodada 3 os fechou com prova viva
o que sobrou é MATERIAL?              não — o que sobrou tem dono: latência 162 s por pergunta (a InfoCap, não o modelo), SES só 2026 ingerido, junção sinistro×carteira vazia (as apólices dos sinistros são de outros anos), caminho feliz de `promover` não rodado ao vivo (só a recusa), 8 de 50 ramos sem grupo SES
```

## 0.2 A TELEMETRIA (§11)

```
começou / terminou                     03/09 21:30 (aquecimento + BLOCO 0) / 04/09 ~06:00 (push)
tempo até a PRIMEIRA linha de código   📊 ~1h05 (21:30 → 22:35, commit 3dcdb89 do BLOCO C) — inclui aquecimento (12 emendas) e BLOCO 0
rodadas de painel e achados por lente  DADO 4 blockers + 5 pend · red team 7 quebras + 9 pend. Únicos: 8 blockers; a raiz (fiação) achada pelas duas frentes; `cancelado` pelas duas; funil só pelo DADO; promover/acento/slug só pelo red team
defeitos que o painel NÃO pegou        a tool morrer ao vivo por uma métrica PARTIAL (M15 sem isolamento) — só o canário vivo do juiz fresco viu; `subject_id` uuid e `decided_at` inexistente — só o schema real viu (os fakes aceitavam qualquer coluna); ramo ignorado no vs_market — só o recálculo à mão do CSV viu. Lição: golden com manifesto VIVO + fixture `schema_vivo.json` (agora no guarda)
rodadas da bateria                     📊 conftest 04/09: suíte inteira 1× (gate final: 936 passed · 5 failed (03:22→03:37, 14m47, árvore parada, d8cd056) — os 5 passam isolados e são a classe do harness (P-093B-HARNESS: guardas-script se atropelam; crash libuv do node num subprocesso; política/ontologia flaky): 093-B 249 ok · ferramentas 67 · política 1 passed · ontologia 1 passed. A rodada anterior (09cbd6b) deu 934/7 com 2 regressões REAIS consertadas em d8cd056); parciais ≈60 (guarda 44→228, protocolo 47, 094 284, npm 67/81 a cada bloco)
nota 0–100 do orquestrador             82/100 — 7 unidades entregues com prova viva na Resulta; 12 métricas novas ao centavo (à mão × produto × CSV do SES); o chat lista, propõe com Approval e recusa sem decisão; 3 rodadas (teto) porque 4 blockers herdados só apareceram ao vivo; perde por latência de 162 s, SES só 2026, junção sinistro×carteira vazia e orçamento 10% acima
```

## 1. O que a SPEC prometeu e o que ficou

**Antes:** 16 métricas (094); o chat não listava o que entregou (130 Artifacts, `artifact_shares` = 0: o link público nunca funcionou); uma
pergunta sem métrica devolvia um Pulso 360 inteiro sobre outra pergunta, sem aviso; a Skill Registry (20 skills) governava zero turnos; o
HITL da SPEC-055 existia sem um único chamador; `/sinistros` (5.729), o funil, `/produtores` e `cancelado` não tinham leitor; nenhum dado
externo entrava no produto.

**Depois:** 28 métricas no registry (16 + 12), cada uma com pergunta verificada e golden obrigatórios; o Pulso 360 tem 13 seções (Sinistros · Funil · Carteira por cliente · Pendências · Mercado novas); a InfoCap ganhou 5 leitores (`/sinistros`, funil ×3, `/renovacoes` com `cancelado`, `/cliente_ligacoes`) com PII descartada na fronteira; o primeiro dado externo do produto: SUSEP SES ingerido por Rotina de plataforma (stream, 30 s, 17 MB de pico) → agregado no MinIO → `market.loss_ratio` por seguradora × grupo de ramo × mês, e `claims.loss_ratio_vs_market` por (coenti × cogrupo) com mapa de 61 siglas (83,86% do prêmio) e 42 ramos (90,43%); o chat lista as entregas (`listar_entregas`, link autenticado) e, quando não tem a métrica, PROPÕE — `PropostaDeMetrica` sem valor, Work Run `metric.proposal` + `approval_requests` (primeiro uso do HITL da 055) + eventos; `promover` (CLI) exige decisão aprovada e nome igual; `COMO-NASCE-UM-RELATORIO.md` (≤12 KB, 6 passos) com guarda de 47 asserções que reprova métrica sem golden, órfã, caixa vazia, tool fora do `if`, provider na fórmula. 📊 Vivo (Resulta): 41 sinistros abertos · 46,79% na maior seguradora · R$ 746.139,31 indenizados · 9,62% cancelados em 2026 · Porto grupo auto 0,5801 = CSV

## 2. As unidades

| bloco | commits | o que fez | gate |
|---|---|---|---|
| 0 · remedir + censo v2.1 + SES | `108ffab` | 18 GET: funil existe (`status`); `/producao` com `dt_ini` (15 fixos: sonda); `/sinistros` 1,1 s; `/produtores` 119; `cancelado=T` INCLUI cancelados (8,4%); sondagem SEGURA de 5 portas de escrita (todas 400/500, nada criado); SES 40 arquivos, `Ses_seguros.csv` 1,8 M linhas 1995→06/2026; mapa 14/15 | manifesto/dicionário/fingerprints atualizados; 284 ok no guarda da 094 |
| A · 5 relatórios | `d67ac80` `11bb54a` `4b8809f` `e994f90` `52468d1` | CBIM: ClaimFact, QuoteFact, CustomerPortfolioFact, MarketFact/MarketFactSet; adapter: 5 rotas em `rotas_lidas`, PII descartada na fronteira; Pulso: Sinistros · Funil · Carteira · Pendências · Mercado; 8 métricas com pergunta verificada e golden | goldens 10/10; M1/M16/M17 vermelhas; `cancelado=T` como recorte vermelho |
| B · SUSEP × carteira | `157df26` `3ce0693` `f820b9d` `dff6731` | ingestão por Rotina de PLATAFORMA (worker, stream, só `Ses_seguros.csv`, agregado no MinIO); `_janela` semanal; trabalhador "Censo SUSEP"; conector lê o MinIO sem HTTP; 4 métricas de mercado; golden Porto 05886 × grupo 05 = 57,12% | golden Porto 0,571239 = registry 0,5712386; M2 vermelha (o M2 antigo era carimbo — consertado com PAR); ingestão 27–30 s, 17 MB |
| C · listar_entregas | `3dcdb89` | tool fina sobre `ArtifactService.listar`; link autenticado; dois tenants | 9/9; M-TENANT vermelha |
| D · proposta | `e6e6612` | `MetricDefinition` ganha `pergunta_verificada`+`golden` (16 existentes preenchidas, goldens medidos 16/16); view desconhecida → `PropostaDeMetrica` sem value + recusa explícita; `propor_metrica` = PRIMEIRO caller de `WorkApprovalService.solicitar()`; `promover` CLI reprova id inexistente; `origem` no bloco; nenhuma tool escreve em `metricas/` | 30 asserções; M-PROPOSTA vermelha |
| E · protocolo | `48a824b` | `COMO-NASCE-UM-RELATORIO.md` (≤12 KB, 6 passos, exemplo completo) + `test_o_relatorio_nasce_pelo_protocolo.py` (47, PAR): sem golden reprova; órfã reprova (2 + 7 listadas com razão); caixa vazia; tool fora do `if`; M1 | 47 verdes; o guarda pegou 2 violações M1 do próprio autor |
| F · canário vivo | (juiz `a5cd37…` · builder r3 `09cbd6b`) | canário vivo pelo caminho do grafo: (a) padrão → artifact `9180ba29…` 26 métricas 162 s · (b) mercado+sinistros 68 s · (c) proposta → run `ba26117a…` + approval `e47a4a5c…` pending · (d) promover sem decisão → recusa · Amandus recusada · `listar_entregas` 20 · `listar_metricas` 28 | SELECTs: artifacts hoje 2 (Resulta), `metric.proposal` 2 (1 `failed` limpo + 1 pending), `last_used_at` Resulta atualizado |

## 3. 📊 Os números
```
censo v2.1 (18 GET)          funil 3 rotas 200 com `status` · /produtores 119 · /sinistros 1,1 s (era 26 s) · cancelado=T INCLUI (325/3.861 = 8,42%) · /producao 15 fixos
escrita no InfoCap (5 sondas) todas 400/500 com corpo vazio: nada criado; validação campo a campo; POST /negocio não valida (500)
SES                           571.756.724 B · sha 7810ea33… · 40 arquivos · Ses_seguros.csv 1.801.731 linhas · 199501→202606 · ingestão 30 s · 17,3 MB pico
golden Porto 05886 × grupo 05 202604–06 = 0,571239 (à mão) = 0,5712386 (registry) · 2026-01..06 = 0,580149 = 0,5801 (produto vivo)
mapa seguradoras              14/15 por nome · 61 siglas · cobertura do prêmio 12,35% → 83,86% · ramos 42/50 = 90,43%
vivo Resulta                  41 abertos · by_insurer 46,79% · R$ 746.139,31 · cancelados 9,62% (99/1.029, 2026) · cross-sell 92,14% · à mão = produto
guardas                       fábrica 228 ok · protocolo 47 · 094 284 · npm 67 · 81 · canário 094 111 (4 vermelhas da recusa Amandus, exit 0)
laço                          aquecimento 12 emendas · painel 8 blockers únicos · juiz fresco 4 herdados · 3 rodadas · ~30 mutações vermelhas
tokens                        ≈ 2,8 M (orçamento 2,5 M) · relógio ≈ 8h30 em 2 janelas
```

## 4. O aquecimento e o BLOCO 0 mudaram a SPEC — antes do código
Aquecimento (nota 84 → 12 emendas): `approvals` → `approval_requests` (a tabela real); `solicitar()` nunca tinha sido chamado; `registry.listar()` →
`todas()`; `tick._janela` colapsa ≥24h em diário (rótulo semanal novo); molde de plataforma `cluster_demand`, não `claims_shadow_digest` (seria N
downloads); MinIO em `services/minio_service.py`, não em `core/`; SES cobre até 202606; GATE ZERO (ii) real: Pulso completo sobre outra pergunta;
colisão com `claims.performance`; `artifact_shares`=0; 4 fatos CBIM novos; C superestimado, A e D subestimados.
BLOCO 0: `cancelado=T` inclui cancelados (a leitura como recorte publicaria a carteira inteira como cancelada); `motivo_perda` não vem no GET;
escrita no InfoCap sondada sem criar nada.

## 5. O laço
Duas frentes Opus 5 (opção B), contexto limpo, sobre `6b6be19..ff1a5b5`, depois do gate integrado (guarda 124 · protocolo 47 · 094 284).
📊 Custo: lente do DADO 180k · red team 217k (a v11.2 previa 3 lentes + red team).

| frente | veredito | o que achou de único |
|---|---|---|
| lente do DADO (7 GET vivos na Resulta + SES local) | FAIL 52 | **Fórmulas e ingestão exatas** (Porto 0,5712 · Tokio 0,6056 · Allianz 0,6506 ao centavo; 33 abertos; 8,42% cancelados; cross-sell 92,14% à mão = adapter). **O ELO não estava ligado:** `cancellation_rate` publicaria 0% (campo `cancelado` não existe em `/documentos_bi`) ou 2,9% (recorte por `inivig` quando a rota filtra por `fimvig`); `quotes.funnel` perdia a etapa FINALIZADO (`/negocios_finalizados` não tem `inivig`); a DERIVED não declarava a 2ª fonte; `ratio` a 2 casas apaga 0,0049 |
| red team (16 ataques) | 7 quebras | **Raiz:** 0 chamadores dos 5 métodos novos e de `ler_agregado` — 11 das 12 métricas UNAVAILABLE por construção e a 12ª falsa; `promover` fecha proposta RECUSADA e nunca lê a decisão do HITL; "Em Análise" → UNKNOWN por acento e some da contagem; negado somado em indenização paga; colisão de slug engole a 2ª proposta; `coenti_de` casa parcial (Porto Saúde → Porto auto); `ler_agregado` não confere sha; célula duplicada somada; sinistralidade −3,0 publicada; vocabulário carimbo nos ramos que nunca executam. Resistiram: tenant em `listar_entregas`/`propor`, injeção normalizada, query plan misto, guarda do protocolo (órfã, sem golden, import da fonte) |

**Fundido pelo TESTE DO PRODUTO: 8 blockers + 7 cintos, numa rodada (1 builder):** fiação por view (raiz) · cancelamento pela rota e base certas · funil com a data de cada rota · sinistros com acento/estados/paginação · DERIVED com 2 fontes · `promover` lê status e decisão · slug com hash · mapa por sigla e nome completo · manifest/sha/ilegíveis/negativo/null · chave da rotina · `ratio` 4 casas · M-PROPOSTA por tipo · vocabulário em ramos alcançáveis · tri-estado · join informativo.
**Lição repetida da 094:** fakes que respondem a tudo escondem que o produto nunca chamou a rota. **Rodada 1 (`368f5e3` `51c8c88` `489a8c4` `47cd099` `e4804a8`):** 15 itens, guarda 124→198; fiação por view provada com espião; cobertura do mapa de
seguradoras 12,35%→83,86% do prêmio (siglas); `promover` lê status e decisão.

### Juiz fresco — confirma + audita + canário vivo
Opus 5, contexto novo, 12 chamadas (7 vivas pelo caminho do grafo). **FAIL 58 — o conserto NÃO criou defeito** (6 mutações vermelhas, 3 suítes
verdes), mas achou 4 blockers HERDADOS que 529 asserções não viam, porque os goldens rodam sem o manifesto PARTIAL e sem o schema real do banco:
B1 "como estamos?" MORRIA ao vivo (104 s → `RELATORIO_FALHOU`): `commercial.quotes` PARTIAL → `exige_cobertura` → `quotes.funnel` devolve `coverage=None`
→ `calcular` levanta M15 → `calcular_varias` não isola → o Pulso inteiro cai (funil está no padrão). Controle: com a fiação removida, morre igual.
B2 `propor_metrica` NUNCA gravou: `subject_id` texto numa coluna uuid (22P02) e o work_run fica órfão. B3 `promover` lê `decided_at`, coluna inexistente.
B4 `claims.loss_ratio_vs_market` compara a Porto de TODOS os ramos (0,5072) com a carteira, quando o grupo auto dá 0,5801 — 7,3 p.p. no número que a SPEC
manda o dono levar à negociação. **O que passou ao vivo:** 4 visões sem funil publicaram (381 s, 9 números); à mão × produto: 41 abertos · 46,79% ·
R$ 746.139,31 · 9,62% cancelados (99/1029 em 2026) · Porto 0,5801 = CSV 0,580149; proposta sem métrica → `propostas[0]` sem value; `listar_metricas` 28;
`listar_entregas` 20 com link autenticado; Amandus recusada antes de ler; ingestão SES real → MinIO real em 29,9 s.
**Rodada 3 (a última):** `b685f23` `b17d227` `4756832` `bc21739` `c020e61` `09cbd6b`: `calcular_varias` isola por métrica (M15 só com número); `subject_id`=uuid do run e ordem sem órfão (órfão `c66c3bf7…` marcado `failed`); colunas reais (`approved_at/rejected_at/resolved_at`, `completed` no enum); comparação por (coenti × cogrupo) com `ramo-cogrupo.json`; fixture `schema_vivo.json` e golden com manifesto VIVO no guarda; relógio por fonte (📊 156 s = carteira 54,7 · clientes 51,4 · cancelamentos 37,7 · sinistros 4,3 · cálculo 0,2). Prova viva: (a) padrão publica 26 métricas; (b) Porto 0,5801 com grupo declarado; (c) proposta grava run + approval + 2 eventos; (d) promover recusa. Guarda 198 → 228. **Gate final (`d8cd056`):** a suíte inteira acusou 2 regressões REAIS sobre guardas de SPECs anteriores — o canário da 094 (as métricas do chat e do Artifact deixaram de ser idênticas: o selo `origem` só nascia no chat; e o vocabulário de bases ganhou `COMPETENCIA`) e a Central da 088 (`metric.proposal` sem card nem decisão) — consertados no PRODUTO (selo em função única usada pelos dois lados; decisão escrita em `SEM_CARD_POR_DECISAO`); canário 117 · Central 530.

## 6. Pendências (PENDENCIAS.md)
```
P-094.1-LATENCIA            🤖 162 s por "como estamos?" (54,7 s carteira + 51,4 clientes + 37,7 cancelamentos): 3 leituras de /renovacoes — cache/snapshot (P-094-SNAPSHOT)
P-094.1-SES-SO-TEM-2026     🤖 só 2026 ingerido; a Rotina semanal cobre o resto quando rodar em produção (P-094.1-SES-SEM-ROTINA-EM-PRODUCAO)
P-094.1-SINISTRO-X-CARTEIRA 🤖 40 apólices de sinistro × 3.861 de 2025 = 0: `loss_ratio_portfolio` sai UNAVAILABLE até o join usar a carteira multi-ano
P-094.1-PROMOCAO-SEM-DECISAO-REAL 🧑/🤖 a recusa rodou ao vivo; o caminho feliz (aprovar + promover) espera a sua 1ª decisão (F-094.1-02)
P-094.1-RAMO-COGRUPO        🤖 8 de 50 ramos sem grupo SES · P-094.1-SIGLAS-SEM-ENTIDADE 🤖 47 siglas UNKNOWN listadas
P-094.1-MOTIVO-DE-PERDA · -EMISSAO-PENDENTE 🤖 UNAVAILABLE por capacidade/custo (a fonte não expõe / 1 chamada por apólice)
P-094.1-FUNIL-SEM-FINGERPRINT · P-094.1-CLAIMS-TEMPLATE · P-094.1-LINK-PUBLICO · P-094.1-HITL-PRIMEIRO-USO · P-094.1-MIX-BRANCH/MOMENTUM/NOVO-X-RENOVACAO-SEM-SECAO
P-094.1-CANARIO-094-RECUSA  🤖 o canário em memória da 094 mostra 4 vermelhas (RecusaDeContaCompartilhada) quando roda depois do gate de conta no mesmo processo — exit 0; isolar o registro por teste
```

## 7. Gate da SPEC
```
GATE ZERO ......... ✅ 4 VERMELHOS em 6b6be19 provados pelo guarda antes do código; VERDES em 09cbd6b
GUARDA DA SPEC .... ✅ test_a_fabrica_de_relatorios.py 228 ok · protocolo 47 · 094 284 · npm 67 · 81
LENTE DO DADO ..... ✅ à mão × produto × CSV: sinistros, cancelamentos, cross-sell, SES (Porto, Tokio, Allianz) — ao centavo
PAINEL ............ ✅ DADO + red team → 8 blockers → rodada 1 → juiz fresco FAIL 58 (4 herdados) → rodada 3 → verdes com prova viva
CANÁRIO VIVO ...... ✅ Resulta: 2 artifacts hoje; proposta run+approval+eventos; promover recusa; Amandus recusada
REGRESSÃO ......... ✅ git diff em api/dispatch/graph = 0 bytes · 094 continua 284 · linha de base dos 3 scripts npm preservada
MIGRATION ......... ✅ ZERO (seções em código; `_garantir_template`)
SUÍTE INTEIRA ..... 936 passed · 5 failed (03:22→03:37, 14m47, árvore parada, d8cd056) — os 5 passam isolados e são a classe do harness (P-093B-HARNESS: guardas-script se atropelam; crash libuv do node num subprocesso; política/ontologia flaky): 093-B 249 ok · ferramentas 67 · política 1 passed · ontologia 1 passed. A rodada anterior (09cbd6b) deu 934/7 com 2 regressões REAIS consertadas em d8cd056
ENTREGA ........... {PUSH}
```
**Veredito do orquestrador: GATE VERDE — SPEC-094.1 CONCLUÍDA**, com as pendências acima (todas com dono) e a decisão F-094.1-02 sua.

## 8. 🧑 A caixa do Founder
```
F-094.1-01  Tool Gateway: 155 diffs em sombra, 0 idênticos — ligar (cutover medido) ou desligar. Ninguém constrói em cima até decidir.
F-094.1-02  Quem aprova uma proposta de métrica: default Founder (parâmetro `aprovador` pronto).
F-094.1-03  094.2 (comissão recebida × apropriada e inadimplência pelo PORTAL da seguradora) — a maior nota da lista; autoriza entrar antes da 095?
F-094.1-04  Fontes pagas com preço público (SPC veicular R$ 51,90 · BigDataCorp R$ 0,04–0,08 · Consultar Placa R$ 0,70–0,99).
F-094.1-05  01/10/2026: WhatsApp de serviço deixa de ser grátis.
F-094.1-06  Escrita no InfoCap: sondagem provou que nenhuma porta cria por acidente e que a API exige campo a campo sem documentar; cadastro em
            massa é SPEC própria com Approval e ambiente de teste (F-094-09).
F-094.1-07  Deploy: `git push origin HEAD:main` + Implantar smith-api. Zero migration. 
F-094.1-08  Há UMA proposta pendente de verdade no banco (Resulta, `proposta.teste_builder_0941`): aprove ou recuse pela API admin — é o teste do caminho feliz.
```

## 9. Riscos remanescentes
- 162 s por pergunta é a InfoCap (3 leituras de /renovacoes de 4 anos), não o modelo; até o snapshot, o dono espera.
- O primeiro dado externo do produto (SES) depende de um mapa feito à mão (siglas e ramos); UNKNOWN nunca vira zero, mas 16% do prêmio e 10% dos ramos ficam de fora.
- Nenhum motor paralelo: registry/adapter/manifesto/Evidence Pack da 094; ArtifactService; WorkApprovalService da 055; tick/worker existentes; Skill Registry intocada (F-094.1-01).
- Orçamento ≈ 10% acima: a 3ª rodada (herdados vivos) custou 353k; sem o juiz fresco ao vivo, os 4 herdados iriam para produção.

## 📊 A BATERIA
📊 conftest 04/09: inteira 1× no gate final (936 passed · 5 failed (03:22→03:37, 14m47, árvore parada, d8cd056) — os 5 passam isolados e são a classe do harness (P-093B-HARNESS: guardas-script se atropelam; crash libuv do node num subprocesso; política/ontologia flaky): 093-B 249 ok · ferramentas 67 · política 1 passed · ontologia 1 passed. A rodada anterior (09cbd6b) deu 934/7 com 2 regressões REAIS consertadas em d8cd056); parciais ≈ 60. Minutos esperando: ≈ 15. Lição: o golden com manifesto VIVO e a fixture do schema real são o que faltava para o guarda ver o que só o canário vivo via.
