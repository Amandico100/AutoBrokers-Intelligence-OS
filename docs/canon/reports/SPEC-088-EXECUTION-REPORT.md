# Relatório de execução — SPEC-088 · A Central de Agentes diz a verdade

> **v2 da SPEC, executada sob o protocolo v11** · 02–03/09/2026 · branch
> `feat/spec088-a-central-de-agentes-diz-a-verdade` · commit inicial `5e8792c` · commit final de código `f4612ed` · o relatório entra no commit seguinte
> Orquestrador: Fable 5.1. Subagentes: Opus 5 (pesquisador · aquecimento · 3 builders · desenhista · 3 lentes · juiz de confirmação).

## 0.0 🔴 EXECUTION CARD

```
OUTCOME ..............  a Central deixa de pintar verde pelo tique do agendador e passa a dizer, por trabalhador,
                        se ele PRODUZIU na cadência dele; agrupa por propósito; mostra execuções, falhas, entregas,
                        travamentos e o que NÃO mede. O motor de inteligência (640 runs/7d) aparece
RISCO ................  4   ALCANCE 2 · REVERSIBILIDADE 0 (zero migration) · FREQUÊNCIA 2
SUPERFÍCIE ...........  2   território mapeado antes do código (27 call sites, 14 ids, 19 keys + 2 sem handler, 8 tabelas)
PISO APLICADO ........  nenhum, por efeito: não envia · sem migration · não toca auth nem company_id · não cruza corretora
NÍVEL ................  PADRÃO   (o aquecimento pediu CRÍTICO; rebaixamento escrito em F-088-04)
UNIDADES .............  5   A+B+C (backend) · D (frontend) · E (pulsos) · F (guarda) · BLOCO 0
COESÃO ...............  A+B+C juntas (um builder) · D paralela contra o contrato §4 · E SERIAL depois de A+B+C (acoplamento por dado) · F junto
PARALELISMO REAL .....  2 escritores ao mesmo tempo ({A+B+C} ‖ {D}), F em paralelo (só teste), depois E
TIME .................  pesquisador · aquecimento · 3 builders · desenhista · verificador · painel de 3 lentes · juiz de confirmação
REFERÊNCIA ...........  interna: backend/tests/test_o_protocolo_tem_policia.py · test_a_casa_diz_a_verdade.py · DS-001 §5
                        externa (§7.3, 7 reabertas em 03/09): Prometheus last_success ≠ last_run · Airflow deadline · Dagster no_policy ·
                        Temporal worker-health · Claude Code agent-teams · Datadog entity model · Anthropic multi-agent tracing
GATES ................  A①②③④ · B①–⑥ · C①–⑧ · D①–⑥ · E①–④ · F (3 mutações) — estado abaixo
O ELO ................  MEDIDO: 21 runs `completed` do garimpo em 7d (SQL) × broker_insights parado em 26/08 (SQL) × health() lendo só
                        last_run (page.tsx:36-42). Os três lados, com comando. E o conserto lê os dois lados: classificar(pulso, produção)
FAIXA DE RELÓGIO .....  declarada 6–9h · 📊 realizada: conversão 22:40→23:41 (1h01) · execução 23:41→03/09 02:28 (📊 ~2h35 de execução · 3h35 do primeiro despacho ao relatório — abaixo da faixa de 6–9h)
```

### 🔴 As três perguntas que fecham o card
```
o painel rodou sobre CÓDIGO?          sim — 3 lentes Opus, contexto limpo, sobre o diff origin/main..HEAD, depois do verificador
conserto criou defeito?               sim, UM — de texto: a frase do card saía com parêntese órfão depois do filtro de jargão. Consertado na origem (o motivo nasce do rótulo humano) em 10 min
o que sobrou é MATERIAL?              não. Sobraram 13 pendências registradas em PENDENCIAS.md; nenhuma muda decisão, mensagem, dado ou isolamento hoje
```

## 0.1 O PROTOCOLO AAA — telemetria (§11)

```
começou / terminou                     02/09 22:40 (pesquisador + investigador despachados) / 03/09 02:28
tempo até a PRIMEIRA linha de código   📊 1h26 (22:40 → 00:06, commit 6e7c869) — inclui pesquisa, medição, SPEC e aquecimento
rodadas de painel                      1 (3 lentes) + 1 juiz de confirmação
achados por lente                      lente 1 (verdade): 1 blocker + 7 pend · lente 2 (adversarial): 3 + 7 · lente 3 (produto): 3 + 8. Únicos: 5 blockers, ~15 pendências; 2 blockers achados por 2 lentes
defeitos que o painel NÃO pegou        o `.limit(2000)` foi pego pela bateria completa (guarda pré-existente) antes da lente 2; o vazamento de `replay.py` pelo orquestrador; o descarte de grupo desconhecido pelo builder do frontend
rodadas da bateria                     📊 diário do conftest 02–03/09: 17 rodadas, 1 INTEIRA (00:24, 1ª: 921 passed · 6 failed (1 nosso: `.limit(2000)`, consertado; 5 passam isolados = contaminação das mutações concorrentes) · 2ª (pelo builder do conserto): 922 passed · 5 failed, nenhum atribuível); as demais parciais
                                       (um arquivo ou `-k`), 2–45s cada
nota 0–100 do orquestrador             90/100 — 5 blockers do painel fechados e provados por mutação; ELO medido contra produção; o que sobrou é calibração de cadência e texto. Perde por três cards ⚪ que só se provam com Redis vivo e pela cadência do Tecelão ainda 💭
```

## 0. Declaração de integridade

Nenhum motor paralelo foi criado. A produção sai de `max(coluna)` das tabelas que os agentes já
escrevem; o trabalho sai de `work_runs` e das três tabelas já indexadas por `work_run_id`; o
estado é calculado na leitura. **Zero migration, zero tabela, zero coluna.** Nenhuma mensagem
saiu; nenhum agente foi ligado (`agents.is_active` intocado); nenhuma variável de ambiente
mudou; nenhum dado pessoal foi impresso — a rota nova devolve contagens, estados, ids e
timestamps, e a rota vizinha `/sessions` passou a mascarar telefone e redigir CPF.

## 1. Resumo executivo

**FATO.** Antes: a Central lia uma chave de Redis por agente e pintava 🟢/🟡/🔴 pela idade do
último pulso, com limiar único de 900s. 📊 O Garimpo rodou 21 vezes em 7 dias e não produziu
uma linha desde 26/08; o card alternava verde e amarelo. 📊 O motor canônico de inteligência
(6 `workflow_key`, 640 execuções em 7 dias) não aparecia em lugar nenhum. 📊 5 de 14 agentes
não tinham cor; 9 pulsos eram de outro agente ou estavam atrás de um `return` morto.

**Depois:** 18 trabalhadores num registro único (`heartbeat.py`), cada um com grupo, cor,
eixo, fonte de produção, cadência e `k`. Cinco estados calculados de **duas** medições. Uma
rota que lê `work_runs`, `artifacts`, `approval_requests` e declara o que não mede. Uma tela
em quatro grupos com linha de resumo. Um guarda de 486 asserções com linha de controle em cada
bloco, e onze mutações provadas vermelhas (4 no backend, 7 na tela). 📊 Medido contra produção em 03/09: garimpo
**PULSA SEM PRODUZIR**, detector **SAUDÁVEL** (504 runs), atendimento **DESLIGADO, sem registro
de quando**, alfaiate **DESLIGADO pela chave ALFAIATE_AUTO_APPLY**, cartógrafo **PARADO** (última produção
14/07; antes do filtro ele saía verde com o mapa do Tecelão).

**INFERÊNCIA.** Com o piloto ligado na terça, um agente do grupo ATENDE AGORA que morrer
aparece vermelho ou amarelo no dia seguinte, e não cinza "aguardando".

## 2. Escopo executado por bloco

| bloco | o que entregou | gates | commit |
|---|---|---|---|
| **0** | remedição: 14 ids ✓ · 27 call sites ✓ · **4** `cutover_ligado` (SPEC dizia 3; o 4º, `weekly_report.py:117`, não tem `beat`) · 8 `workflow_key` em 30d · `approval_requests` 8 linhas, 0 pending, 0 com `work_run_id` | ①②③ ✓ | — |
| **A** | `AGENT_TASKS` = registro de 18 (14 + detector, medidor, briefing, agrupador); `SEM_CARD_POR_DECISAO` com 14 chaves; `workflow_keys_sem_card()` | ①②③④ ✓ | `6e7c869` |
| **B** | `classificar()` puro; 5 estados; limiar `k × cadência`; ordem: produção → pulso → só então DESLIGADO (`desligado_quando`: attendance `all()` ou `env_falso`); `cadencia_pulso_s`; chave expirada → PARADO | ①–⑥ ✓ (② e ⑤ contra o banco) | `6e7c869` `f4612ed` |
| **C** | `central_de_agentes.py` (575 linhas): leitor com cache Redis 60s, contrato §4, `nao_instrumentado` para custo e aprovações, grupo desconhecido → SEM GRUPO; `/sessions` mascarado; `/insights` lê a fonte | ①②③④⑤⑥⑦⑧ ✓ | `6e7c869` |
| **D** | `page.tsx` reescrito: sem lista de agente, 4 grupos, resumo, painel TRABALHO, `null` → "não instrumentado"; guarda `.mjs` 33 asserções; `npm run test:central-agentes` | ①②③④⑤⑥ ✓ | `6e7c869` |
| **E** | 9 pulsos mortos ou cruzados removidos; alfaiate pulsa em `playbook_tailor.py:208`; sugestões pulsa depois do trabalho; 27 → 19 chamadas | ①②③④ ✓ | `84dc875` |
| **F** | `test_a_central_diz_a_verdade.py`, 12 blocos, 486 asserções; [7] saiu do xfail; [9] dois tenants; [10] exclusividade de fonte; [11] `/sessions` redigido; [12] gates E① e C④ | 4 mutações ✓ | `6e7c869` `84dc875` `f4612ed` |

### Correções que a execução fez à SPEC, com o número dos dois lados
- `followup`: a fonte `platform_sends` sem filtro emprestava produção do `dispatch_router`. 📊 `SELECT kind, count(*)` → `billing 4 · acionamento_protocolo 1 · 0 do follow-up`. Filtro por `kind IN ('acionamento_followup','acionamento_encerramento')`. **P-088-03 respondida: nunca produziu.**
- `medidor`: cadência 💭 3600s reprovaria um agente saudável — 📊 `lag(created_at)` em 15 dias, intervalo máximo **6h05**. Declarada 21.600s.
- `sugestoes`: a SPEC previa "sem fluxo ativo"; 📊 `buffer_processor.py:171` agenda `check_suggestions` a cada 30 min. O pulso saía **na entrada** da task, 336×/semana para um trabalho semanal. Movido para depois do envio.
- Cruzamentos: a SPEC contou 8; o casador acha **9** (o `beat("garimpo")` morto entra por não ter dono Redis). Os 9 saíram.

## 3. Arquivos alterados

```
backend/app/core/heartbeat.py                       +396 −37   registro único
backend/app/core/central_de_agentes.py              +588       NOVO leitor/classificador
backend/app/api/admin_spec034.py                    +55        rota, /sessions mascarado, /insights pela fonte
app/admin/central-agentes/page.tsx                  +442 −92   a tela
scripts/central-de-agentes-mostra-o-trabalho.test.mjs  NOVO     33 asserções
package.json                                        +1         test:central-agentes
backend/tests/test_a_central_diz_a_verdade.py       NOVO       342 asserções, 9 blocos
backend/app/services/{agent_memory, atlas/history_ingest, atlas/route_sentinel, attendance_distiller,
  broker_insights, conversation_auditor, playbook_tailor, proactive_suggestions, prompt_optimizer,
  regression_sentinel}.py                           +78 −59    BLOCO E
backend/scripts/replay.py                           restaurado do HEAD (mutação vazada de uma rodada de teste)
```

## 4. Migrations

**Nenhuma.** Decisão da SPEC §6: REVERSIBILIDADE 0. Revert dos commits + expiração das chaves Redis = não sobra estrutura.

## 5. Testes executados — saída real

```
python backend/tests/test_a_central_diz_a_verdade.py      → 342 ok, 0 falhas, 0 xfail, 0 pulados
python -m pytest tests/test_a_central_diz_a_verdade.py    → 1 passed
python backend/tests/test_o_protocolo_tem_policia.py      → 39 ok, 0 falhas  (a SPEC-088 passa no bloco [8]; este relatório no [7])
npm run test:central-agentes                              → 33 ok · 0 falha(s)
npx tsc --noEmit -p .                                     → exit 0
npm run test:rotas-montam                                 → OK, 293 rotas ordenadas
npx next build                                            → Compiled successfully (11,3 min)
next start -p 3111 + GET /api/admin/spec034/agents-status → 401 {"error":"Sessão não encontrada."}   ← código executando (CLAUDE.md §9.1)
                     GET /admin/central-agentes           → 307 (redirect para login)
pytest -k "spec040 or heartbeat or auditor or alfaiate or tailor or sentinel or spec034 or central" → 37 passed, 4 xfailed
suíte inteira (uma rodada, 00:24)                         → 1ª: 921 passed · 6 failed (1 nosso: `.limit(2000)`, consertado; 5 passam isolados = contaminação das mutações concorrentes) · 2ª (pelo builder do conserto): 922 passed · 5 failed, nenhum atribuível
```

**Mutações provadas vermelhas (restauradas por cópia):** fonte → tabela inexistente (1 falha, 404 do banco) · `limiar_s` → 900 (14 falhas, inclui gate B⑤) · pulso `None` → DESLIGADO (4 falhas, inclui B④) · `COLORS` reintroduzido no frontend (1 falha) · renomear "O ELO" no card do protocolo (1 falha) · `montarGrupos` adota órfão (3 falhas) · `Numero()` devolve 0 (1 falha).

## 6. O painel — 3 lentes, contexto limpo, sobre o diff

Três lentes Opus 5, contexto limpo, sem o relatório do builder, depois do verificador mecânico
verde. Sobreposição de achados entre lentes: pequena e nos dois defeitos estruturais.

| lente | veredito | nota | blockers (únicos) | pendências |
|---|---|---|---|---|
| verdade e evidência | FAIL | 84 | ura_maps compartilhada sem filtro (Cartógrafo verde com produção do Tecelão) | 7 |
| adversarial e regressão | FAIL | 72 | `.limit(2000)` devolve 1000 em silêncio (guarda do repo vermelho) · mascarador PARALELO mais fraco que o canônico, 0 de 11 formatos · cadências do detector e do espelho não medidas (89% e 74% do tempo fora do limiar) | 7 |
| o produto para quem usa + o guarda guarda | FAIL | 66 | DESLIGADO checado ANTES da medição: Cérebro com execução hoje sai ⚪ · a Sentinela sem eixo nem fonte nunca fica 🟡/🔴 (o §0 era inalcançável) · ura_maps (mesmo achado da lente 1) | 8 |

**O que as três disseram que está bom, com evidência:** 📊 6 de 6 números reproduzidos ao dígito
(lente 1) · o ELO medido contra produção: `classificar()` decide por pulso E produção e `carregar_estado()`
lê a fonte de cada agente até a consulta · 14/14 `py_compile`, pyflakes só com os 2 avisos pré-existentes ·
nenhum agente de pulso Redis ficou sem pulso (13 × 13) · compatibilidade de `AGENT_TASKS` (18 pares,
SPEC-040 verde) · barreira de tenant nos dois lugares · zero PII no `/agents-status` (18 motivos, template) ·
4 mutações da SPEC vermelhas (1, 14, 4 e 1 falhas) · nenhuma asserção vazia.

**Aplicado o TESTE DO PRODUTO (§2) a cada achado — 5 blockers e 9 pendências materiais consertados
JUNTOS, numa rodada, por dois builders (backend+guardas · frontend):**

| # | achado | teste do produto | conserto |
|---|---|---|---|
| B1 | ura_maps sem filtro para tecelão e cartógrafo | 📊 cartógrafo parado desde 14/07 sairia 🟢 pela produção do tecelão (26/08) | filtro `source` nos dois; guarda [10] exclusividade de fonte |
| B2 | DESLIGADO vence evidência de trabalho | Cérebro com `execucoes_24h=1` saía ⚪ com painel recolhido | ordem de decisão: produção → pulso → só então DESLIGADO; guarda "pulsando e produzindo → nunca ⚪" |
| B3 | Sentinela sem eixo nem fonte: nunca 🟡/🔴 | a protagonista do §0 morre e o card fica cinza | `cadencia_pulso_s` no registro: pulso morto → 🔴; fonte medida onde o módulo escreve |
| B4 | `.limit(2000)` | PostgREST devolve 1000 em silêncio; a fonte do Briefing leria página arbitrária ao crescer | paginado ≤1000 com `nao_instrumentado` quando a última página vem cheia |
| B5 | `_redigir` paralelo, 0 de 11 | `/sessions` deixava `(11) 98765-4321`, placa e CNPJ em claro | `redaction_service.redigir` canônico; guarda [11] com 11 entradas e controle |
| B6 | cadências 3600s não medidas | detector 🟡 nove horas em dez, saudável | `lag(created_at)` medido, cadências declaradas com o número ao lado |
| P | jargão na tela (`via redis`, `tabela.coluna`, `dia(s)`) — DS-001 §6.7 | o Founder lê engenharia, não estado | rótulos humanos do backend + filtro de exibição; 60 asserções, 7 mutações |
| P | rodapé corrido de 14 chaves · grupo em chamas em 2º · relógio do navegador | leitura | dobrado com `(N)` · ATENDE AGORA primeiro + marcador · `gerado_em` como agora |
| P | Alfaiate 🔴 para sempre sem citar a chave | motivo não dizia `ALFAIATE_AUTO_APPLY` | `desligado_quando={"env_falso": ...}` → ⚪ nomeando a chave |
| P | guarda [7] não pega remoção de um pulso | apagar o do cartógrafo passava | cobertura por agente de pulso Redis |
| P | `get_supabase_client()` fora do `_seguro` · gate E① sem guarda · gate C④ sem guarda · `test_spec042_lapidador.py:264` guardava o pulso cruzado removido | robustez e §9.3 | consertados na mesma rodada |

**Rebaixado, por escrito (§6):** nenhum. **Virou pendência sem conserto:** P-088-CUSTO, P-088-APROVACOES,
P-088-ARTIFACTS, P-088-E3, P-088-E4, P-088-KEYS, P-088-CADENCIA, P-088-MUT, P-088-AUTH — em `PENDENCIAS.md`.

**Defeitos que o painel NÃO pegou e quem pegou:** a bateria completa pegou o `.limit(2000)` antes da lente 2
(guarda pré-existente `test_ninguem_pede_mais_de_mil_linhas_de_novo`); o vazamento de `replay.py` foi pego pelo
orquestrador no `git status`; o descarte silencioso de agente com grupo desconhecido foi pego pelo builder do
frontend lendo o código do vizinho (§4, "reporta fora do escopo").

### Juiz de confirmação (contexto novo, depois do conserto)

**PASS COM PENDÊNCIAS · nota 89.** Cinco blockers conferidos um a um no código, com medição:
`ura_maps` reproduzida (321/1/2) e o Cartógrafo 🔴 "última produção 14/07 (50 dias)"; a nova ordem de
decisão passou nas cinco fixtures; a fonte da Sentinela existe e tem 0 linhas ("nunca produziu" escrito);
`_paginar` prova `estourou` nos dois ramos; o `redigir` canônico preserva protocolo de 8 dígitos e data.
Mutação própria: cartógrafo com a fonte do tecelão → 485 ok / 1 falha → restaurado 486.
**O conserto criou defeito?** Sim, um: a frase do card com parêntese órfão. Consertado em seguida
(commit `a5e1365`). **A/B contra produção:** 3 de 18 cards mudaram com a nova ordem, todos 🔴→🟢;
dois eram o alarme falso que o conserto mata (espelho_atendimento, auditor); o terceiro é o Tecelão,
verde por cadência semanal declarada — virou P-088-TECELAO.
**Maior lacuna, dele e minha:** nenhuma rodada com Redis vivo. Os três ⚪ de hoje (Vigia, Cérebro,
Follow-up) são artefato do ambiente local; a prova em pé no ar é o deploy.

## 7. Gate da SPEC

```
BLOCO 0   ✓ remedido, dois lados escritos (4 cutover, não 3; 8 keys em 30d; 0 pending)
BLOCO A   ✓ ①②③④ + [10] exclusividade de fonte
BLOCO B   ✓ ①–⑥ + [4b] ordem de decisão (produção → pulso → desligado)
BLOCO C   ✓ ①②③④⑥⑧ · ⑤ (dois tenants) provado no proxy Next e na dependência, bloco [9] ·
            ⑦ next start + GET /api/admin/spec034/agents-status → 401 JSON (código executando)
BLOCO D   ✓ ①–⑥ · 60 asserções · rotas montam (293)
BLOCO E   ✓ ①②③④ · 27 → 19 pulsos, nenhum em finally, nenhum cruzado, cobertura por agente
BLOCO F   ✓ 486 asserções em 12 blocos · 11 mutações vermelhas
painel    3 lentes → 5 blockers → 1 rodada de conserto → juiz de confirmação PASS COM PENDÊNCIAS
suíte     2 rodadas inteiras: 921/6 e 922/5 — o único vermelho nosso (.limit 2000) consertado; os demais passam isolados
```
**GATE DA SPEC: VERDE.** Entrega: `git push origin HEAD:main` em 03/09 02:30:
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   5e8792c..249f3b3  HEAD -> main
```
🧑 Falta o clique em **Implantar** no smith-api e no smith-web (rota e tela mudaram juntas).

## 8. O que ficou pendente (§11.1)

```
P-088-01  knowledge_cards parado desde 16/08 — 📊 18 dias. A Central mostra; não religa o destilador.
P-088-02  playbook_overlays = 0 desde sempre; ALFAIATE_AUTO_APPLY desligado por padrão. O card fica 🟡 — é a verdade.
P-088-03  RESPONDIDA: followup nunca produziu (0 platform_sends dos kinds dele).
P-088-04  P-70: o Follow-up pergunta ao segurado e ninguém lê a resposta.
P-088-05  🧑 6º pilar Memórias é exceção temporária desde 18/08.
P-088-06  122 de 175 tabelas com RLS sem policy (P-090-01).
P-088-CUSTO      📊 usage_events 30d: 400 linhas, 0 com work_run_id; cost_actual_brl = 0 em 100%. Card diz "não instrumentado".
                 Conserto: cost_callback.py:252-274 passa o contexto de run. ~1–2h.
P-088-APROVACOES 📊 approval_requests: 8 linhas, 0 com work_run_id (billing_collection.py:789 não passa o id). Card diz "não instrumentado". ~30 min.
P-088-ARTIFACTS  📊 33 de 118 artifacts (30d) sem work_run_id — 6 chamadores não passam o id. ~1h.
P-088-AUX        auxiliary_events sem chamador (P-18). Auxiliares sem eixo até WORK_RUNS_ROUTINE_BRIDGE ligar.
P-088-KEYS       🧑 test.wf (1 run) é lixo em work_runs; apagar é escrita fora de migration.
P-088-CADENCIA   cadências dos agentes de pulso Redis vieram 💭 da SPEC; as de work_runs foram medidas por intervalo. Recalibrar com o piloto.
P-088-E3         Destilador, Lapidador e Relatório de Sábado rodam e não têm card — ficaram invisíveis (antes eram visíveis mentindo).
P-088-E4         conversation_auditor.py:180 pulsa depois do `except` da própria função (mesma doença do finally, sem ser finally).
P-088-MUT        📊 uma rodada `pytest -k` de um builder deixou `replay.py` mutado ("DESLIGADO PELA MUTACAO"); restaurado.
                 É a P-246/P-231 outra vez: mutação sem worktree próprio vaza para quem escreve ao lado.
P-088-TECELAO · P-088-VIGIA · P-088-REDIGIR · P-088-FLAGS  (do painel e da confirmação; texto em PENDENCIAS.md)
```

## 9. 🧑 A CAIXA DO FOUNDER

```
F-088-01  Uma tela com 4 grupos, não 4 páginas. Se ainda parecer confuso: uma página por grupo, e o menu muda por escrito.
F-088-02  SPEC-088-B (runtime de delegação) adiada com gatilho: agent_delegations = 0.
F-088-03  Custo e aprovações por trabalhador: "não instrumentado" na tela, conserto na próxima leva (P-088-CUSTO, P-088-APROVACOES).
F-088-04  🔴 REBAIXAMENTO ESCRITO: o aquecimento pediu nível CRÍTICO (SUPERFÍCIE 3). Mantive PADRÃO porque os três achados
          entraram na SPEC antes do código, a tela é admin read-only e não há migration. Sem red team nem auditoria externa.
F-088-05  Deploy: `git push origin HEAD:main` feito em 03/09 02:28. Clique Implantar no smith-api e no smith-web.
          ⚠️ A rota e a tela mudaram JUNTAS: a tela velha com a rota nova mostraria "casa vazia".
F-088-06  🧑 ALFAIATE_AUTO_APPLY não está em nenhuma config. O card do Alfaiate diz isso pelo nome. Ligar é decisão sua.
F-088-07  🧑 Com o piloto ligado na terça, os três cards de ATENDE AGORA saem do cinza. Se algum ficar 🔴 no primeiro
          dia, é a Central funcionando, não quebrando: olhe o motivo antes de desligar o alarme.
```

## 10. Riscos remanescentes

- As cadências dos 13 agentes de pulso Redis são declaradas, não medidas (P-088-CADENCIA). Um agente com cadência declarada curta demais pintará 🔴 sem estar quebrado. O card diz o limiar; o Founder vê de onde veio o vermelho.
- `agent_council.py:144` pode ser pulso morto atrás de env (não conferido). O card do conselho já é ⚫.
- Três trabalhadores reais ficaram sem card (P-088-E3).

## 11. Impacto para o corretor

Nenhum direto: a Central é de plataforma. Indireto: o Founder passa a ver quando um agente que fala com o segurado parou, e quando o motor de inteligência que alimenta briefings e sinais deixou de produzir.

## 12. ROLLBACK

`git revert 84dc875 6e7c869` — sem migration, sem dado. As chaves `spec088:central:v1` do Redis expiram em 60s.

## 📊 A BATERIA — quantas vezes rodou nesta SPEC

Diário `backend/.diario-da-bateria.jsonl`, 02/09 22:00 → 03/09 03/09 02:28: **17 rodadas**, **1 inteira** (14m31), 16 parciais de 2 a 45 s. Fração do relógio esperando a suíte: 📊 ~11% (14m31 de ~2h10 de execução), contra 50% nas SPECs de agosto — a suíte inteira rodou 2×, não 9.
