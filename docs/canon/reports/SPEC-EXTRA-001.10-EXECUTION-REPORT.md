# SPEC-EXTRA-001.10 · O portal de vidros de ponta a ponta — relatório de execução

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `083eeca`

```
OUTCOME ..............  o agente coleta ANTES o que o portal pede, abre o pedido em qualquer seguradora que o portal
                        publica, LÊ o desfecho que o portal decidiu e devolve nº + franquia + próximo passo; resposta
                        desconhecida = handoff com dossiê + fila de aprendizado
RISCO ................  8 = alcance 3 + reversibilidade 3 + frequência 2
SUPERFÍCIE ...........  3
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus 5 xhigh · juiz Fable ‖ red team Fable
O FIO ................  SPEC §2 · tests/test_o_fio_do_portal_de_vidros.py + test_e00110_a_costura_do_agente_ao_desfecho.py
PARALELISMO REAL .....  2 builders com arquivos disjuntos (A = journeys/vidros_* · C = app/* + freio) + costura em série
UNIDADES .............  SPEC §3 (17; 3 nasceram da captura nº 1: desfecho, reparo, contato)
COESÃO ...............  SessaoVidros ↔ vidros_estado ↔ vidros_apifirst ↔ vidros_api com um dono só
TIME .................  2 leitores Opus · 2 builders Opus · juiz ‖ red team Fable · confirmação · docs
REFERÊNCIA ...........  interna tests/test_spec074_a_fronteira_material_executada.py · externa: proposta §13 (6 URLs)
GATES ................  G1 · G1b · G1c · G2–G9 · G11 verdes · G10 (canário) na caixa do Founder
O ELO ................  "loja/agenda aparece PORQUE opcoes-disponiveis manda": A, B e B→A medidos (bundle + 3 desfechos)
FAIXA DE RELÓGIO .....  declarada 10–14 h 💭 · real: §10
```

**SPEC:** `specs/SPEC-EXTRA-001.10-…md` · **Branch:** `feat/extra-001-10-o-portal-de-vidros-ponta-a-ponta` · **Preflight** 📊 20/09:
`HEAD..origin/main` = 0 · `origin/main..HEAD` = 0 · HEAD `083eeca` · **HEAD final** `b246a4f` · 📊 `git diff --stat 083eeca HEAD` →
**32 arquivos · 9.207 inserções · 260 deleções · 8 commits**.

## 1. BLOCO 0 — o que foi remedido antes de codar (📊 20/09/2026)

| # | medido 📊 (a proposta dizia outra coisa onde há ⚠️) | comando | consequência |
|---|---|---|---|
| B0.1 | PATCH: **0 ocorrências**, 12 métodos na sessão | `grep -n PATCH journeys/vidros_sessao.py` | o PATCH nasce aqui, 8 chaves |
| B0.2 | `FRONTEIRA_MATERIALIZAR="gravar_questionario"` :233 | `sed -n 228,240p vidros_estado.py` | vira `fronteira_materializar_de(categoria)` |
| B0.3 | ⚠️ **11** `EP_` nunca chamados, não 9 | laço `grep -rn $ep` (proposta §4) | `ESTADO_DO_ENDPOINT` + `pode_sair` |
| B0.4 | 3 slugs fechados, um é ITAU (`vidros_apifirst.py:102`) | `sed -n 100,107p` | a lista morre; slug por DADO |
| B0.5 | ⚠️ prompt na linha **136** (não 133) | `grep -n IMEDIATAMENTE app/core/prompts.py` | cidade entra sem o prompt enumerar |
| B0.6 | 354/188/41/14/29/44 no HAR de lataria: **idêntico** | `portal_factory.py lab har` | o replay offline é fiel |
| C-A | freio global (`journeys/__init__.py:294`) **LIGADO** em produção | env do Founder | o freio novo é por job, e só ESTREITA |
| C-B | token só depois do `PUT corretores` | leitor sobre `importar_har` | a ordem da escada é lei |
| Q-C | `NomeFantasia` "YELUM SEGURADORA", slug `LIBERTY`, cód. 56 | `GET /seguradoras/` | apelidos em triplas |
| 🔴 B0.7 | **ZERO escritas** nos 3 HAR da Yelum: `LIBERTY` não estava nos 3 slugs | replay pelo motor velho | o API-first estava **morto para 14 das 17** seguradoras conhecidas |

### 1.1 🔴 O achado central (captura do para-brisa, 20/09)
Quem decide **loja × agenda** é o **PORTAL**, em `GET /agendamentos/opcoes-disponiveis` (20 chaves), roteadas na ordem do bundle:
`IrParaConclusao|ExisteVistoriaCriada|ExisteAgendamento|ExisteOrdemServico|VistoriaFinalizada` ⇒ **conclusão** (loja já atribuída,
sem agenda) · `PermiteVistoria*|RealizarVistoria` ⇒ **vistoria** (0 exercícios) · `DisponibilizarAgendamento` ⇒ **agenda**.
📊 para-brisa com reparo → conclusão · lataria → conclusão · vidro de porta (troca) → agenda com 1 loja e `Blocos: []`: mesma
seguradora, mesma apólice, mesma categoria ⇒ **não é atributo da peça**. Mais 5 fatos: o **reparo** (`regras-reparo` →
`ExibirDialogDeReparo` → `PUT alterar-reparo`) era invisível ao código (0 ocorrências) · `ScriptFinalizacao` **reescreve a si
mesmo** (só vale depois de `opcoes-disponiveis`) · P0-3 confirmada com N=2 · 3 de 4 capturas gravaram `Tipo 21 CELULAR CORRETOR`
⇒ `PossuiTelefoneRecebeWhatsapp:false` · `DataSinistro` viaja ISO `T03:00:00.000Z` em 4/4 · `GET /seguradoras/` = **38**.

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate · saída real | commit |
|---|---|---|---|---|
| A | journey até o desfecho: PATCH 8 chaves · corretores+solicitantes · fronteira por categoria · `ler_desfecho` · reparo · `ESTADO_DO_ENDPOINT`/`pode_sair` | `vidros_apifirst` · `vidros_api` · `vidros_sessao` (+17 métodos) · `vidros_estado` · `vidros_questionario` · `_replay_vidros` | `test_o_fio_do_portal_de_vidros.py` → **66 asserções, rc=0** (3 HAR reais) | `7b8cc37` |
| A | seguradora POR DADO: lista ao vivo + 1 tabela de apelidos | `vidros_api.py:615 resolver_seguradora` | `…a_escada_e_a_seguradora.py` → **143, rc=0** | `7b8cc37` |
| C | cidade bloqueante · perguntas por família · contato do segurado · freio por job · work_run · desfecho em português · fila de aprendizado | `portal_params` · `portal_tool` · `prompts` · `perguntas_do_portal_de_vidros` · `vigia_do_portal` · `journeys/__init__` · `worker` | `test_e00110_c_*.py` → cidade/prompt **45** · perguntas **88** · ficha **45** · desfecho **131** · freio **44**, rc=0 | `c051d8b` |
| A↔C | **a costura**: 7 quebras reais entre o que o agente monta e o que a journey lê (peça × catálogo, peças de lataria, perímetro que virava "Não sabe", `DataSinistro`, uma tabela só de seguradora, lataria/para-choque) | os dois lados | `…a_costura_do_agente_ao_desfecho.py` → **161, rc=0** | `ee9ed86` |
| A+C | **coletar ANTES o que pararia DEPOIS**: causas medidas como dica · toda pergunta vista numa tela real TRAVA o pedido · resposta de um slot não responde outro · "NÃO SABE" nunca pelo robô | `vidros_api.py:811` · `perguntas_do_portal_de_vidros` | os 8 testes da área, rc=0 | `a4bd3e7` |

📊 15 testes vizinhos rerodados (spec020 30/0 · spec073 · spec074 ×4, 151 no maior), todos rc=0.
🔴 Tudo atrás da flag `PORTAL_VIDROS_API_FIRST`, **DESLIGADA**: o que atende hoje é o caminho DOM, inalterado.

## 3. Migrations — **nenhuma**
Nada de SQL, DDL ou backfill: escreve em tabelas que já existem (`portal_jobs`, `work_runs`, `tela_cega`) pelos repositórios do produto.

## 4. O julgamento — 1 rodada paralela (juiz ‖ red team, cegos) + confirmação
⚖️ **Juiz Fable** sobre `a4bd3e7`: **REPROVA, 74**, 4 blockers · 🗡️ **Red team Fable** (cego, mesma base): **55**, 7 blockers ·
🏁 **Confirmação** por juiz novo sobre `4e14a1f`: **LIBERA COM PENDÊNCIAS, 84**.

| # | quem achou | achado (📊 reproduzido pelo motor real) | conserto |
|---|---|---|---|
| 1 | ⚖️ juiz — **EXCLUSIVO** | 🔴 **regressão em PRODUÇÃO com a flag desligada**: todo job DOM de sucesso entrava na fila de aprendizado e perdia a marca `entregue_ao_agente` ⇒ o Vigia mandava 2ª mensagem ao segurado | `_o_job_deu_certo`; a marca é fundida na evidence RELIDA |
| 2 | ⚖️ juiz + 🗡️ red team | a **causa** era escolhida por "palavra distintiva": "quebra acidental" ⇒ `QUEBRA INTENCIONAL OU VOLUNTÁRIA`; "nao sei" ⇒ `VIDRO NÃO SOBE OU DESCE` | a passada morreu: causa literal ANTES da fronteira, igualdade depois |
| 3 | ⚖️ juiz + 🗡️ red team | falha de `GET /atendimentos` ou de `PUT alterar-reparo` depois do protocolo terminava `done` com desfecho **inventado** ("está com o analista") | `parar()` ⇒ `desfecho_ilegivel` / `reparo_nao_gravado`, com o número |
| 4 | ⚖️ juiz + 🗡️ red team | paradas depois do protocolo **prometiam continuação que não existe**, omitiam o número e o run ficava `completed` | 26 paradas com número primeiro e sem promessa; run só conclui com `done` |
| 5 | 🗡️ red team — **EXCLUSIVO** | **peça**: "vidro lateral" ⇒ `LANTERNA … LATERAL LED` (a passada por família, código novo) | a identidade do ITEM tem de ser a família dita |
| 6 | 🗡️ red team — **EXCLUSIVO** | **cidade**: "Curitiba" + UF assumida da apólice ⇒ `CURITIBANOS/SC` (continência) | UF escrita pelo segurado; só igualdade |
| 7 | 🗡️ red team — **EXCLUSIVO** | **perímetro**: `br` casava por substring dentro de "queBRou" ⇒ gravava **Rodoviário** | enum fechado; vocabulário por palavra inteira, antes da fronteira |
| 8 | 🗡️ red team — **EXCLUSIVO** | a mensagem de **agenda** imprimia um dicionário Python ao segurado (`{'mes': 8, 'dias': […]}`) — e o G1c estava verde por cima | `dias` = lista de `DD/MM`; a costura proíbe `{`, `[`, `None` na mensagem |
| 9 | 🗡️ red team (pendências consertadas junto) | allowlist só com separadores **abria** · `pode_sair` sensível a maiúsculas/barra · flags de fraude ignoradas · `aceita_reparo` só entendia 6 palavras · o fio não guardava o tipo de telefone | fail-closed nos três primeiros; normalização antes da fronteira; o fio afirma `CELULAR SEGURADO` |
| 🔴 10 | 🏁 confirmação — **EXCLUSIVO**, e **criado pelo conserto** | nome de cidade mutilado no meio: "Passo de Torres/SC" ⇒ `PASSO TORRES`, e o pedido abria antes de a igualdade falhar | 📊 293 cidades, ida e volta: 6 falhas → 0 |
| 11 | 🏁 confirmação — **EXCLUSIVO** | `agenda`/`vistoria` terminavam `done`: a mensagem dizia "a equipe confirma" e **nada avisava a equipe** | o run não conclui (a Fila enxerga) e o Vigia alerta o suporte sem depender do modelo |

⚠️ Antes do julgamento, a **costura** (teste do fio agente → journey → mensagem) já tinha achado **7 quebras** que nenhum gate de
unidade via — entre elas o perímetro que virava `N` ("Não sabe") para "na cidade". 📊 Exclusivos: juiz 1 · red team 4 · confirmação 2.

**Aberto na confirmação:** job DOM `done` sem número extraído ainda entra na fila de aprendizado (resíduo, §9).

**⚠️ Incidente:** o 1º juiz rodou um script que alcançou o **cliente Supabase REAL** com `company_id` falso (esqueceu o dublê). As
duas chamadas deram `APIError`; 📊 SELECT de 20/09 → **0 linhas** em `tela_cega`, `work_runs`, `portal_jobs` para
`company_id like 'aaaaaaaa-0000-4000-8000-%'`. Virou **P-E00110-A17** (teste que toca `portal_tool` falha alto se alcançar o real).

**⚠️ Quebras de regra declaradas:** (1) **o aquecimento de 17 perguntas não foi rodado** — o v13 §8 diz que aquecimento nunca
entra, e o BLOCO 0 saiu da captura real (D-E00110-08: pular **75** × rodar **60**); (2) **o contexto do gerente passou do teto de
300 k** (📊 pico **366 k**), com fatias delegadas e a SPEC num chat só (autorização permanente nº 3 do Founder); (3) **`6f74e60`
foi commitado antes de reconferir o guarda e não o consertava** — `b246a4f` consertou.

## 5. O conserto único
`4e14a1f` juntou os 11 blockers numa passada, sob a regra que os explica todos: **RIGOR ANTES DA FRONTEIRA, só IGUALDADE DEPOIS**
— antes de materializar, tudo é conferido contra o que o portal publicou; depois, o que não bate vira parada com número. `7b965a2`
fechou o que a confirmação achou. 📊 **20 mutações** rodadas e restauradas por cópia (`ItemRemovido` a mais · `−CodigoZona` ·
script lido antes da hora · fronteira fixa · roteador invertido G6 · `agendamentos` promovido G7 · cidade fora de `TRANSPORTAVEIS`
· allowlist que liga o freio · família de retrovisor apagada · desfecho conhecido na fila · `cidade_servico` renomeada de um lado
só · filtro de slot · "NÃO SABE" pelo relato · `_o_job_deu_certo` removido · identidade da peça desligada · perímetro por
substring · "de" tirado do meio da cidade): **todas VERMELHAS**.

## 6. A bateria — 📊 1 rodada inteira, triagem NOMINAL contra a linha de base
📊 21/09/2026, `cd backend && python -m pytest tests -q`: **36 failed · 1200 passed · 34 xfailed · 1 xpassed em 3.113 s**. Contra
`reports/BATERIA-LINHA-DE-BASE.txt` (35): **1 falha nova** — `test_o_pulso_360_nao_pertence_a_infocap` (a descrição gerada da tool
citava o provedor pelo nome; teto de menções 8 × 7): **nossa**, consertada em `b246a4f` e **reconferida isolada, rc=0**.
**0 falhas sumiram** ⇒ o conjunto volta a ser o da base (**35**). ⚠️ Os testes desta área são scripts:
`pytest tests/<arq>.py` isolado dá `INTERNALERROR` (**P-E00110-A6**); a bateria inteira os coleta e eles passam dentro dela.

## 7. O que ficou fora, e o gatilho que o faz voltar
`POST agendamentos`/`direcionamentos` (0 exercícios: o segurado escolhe loja e dia na conversa e a equipe conclui no portal;
gatilho = a captura do agendamento concluído) · fotos/vistoria · domicílio · `finalizar` · `abandonar` (1 exercício, falta
decisão) · `cancelar` (exige `motivos-cancelamento`, 0 exercícios) · roda/pneu · polimento de farol · livre escolha · 2º motor
`atendimentos/respostas` · Bradesco (D-PILOTO-17) · a Fila ler o run do portal (P-E00110-C-03) · 🔴 **a journey de CONTINUAÇÃO
(P-E00110-A11)**: o token do portal vive **só em memória**, então toda parada depois do protocolo termina em mão humana — é o
coração da **EXTRA-001.10.1**. O **CANÁRIO (G10) NÃO rodou**: exige Implantar + apólice/veículo de teste (CLAUDE.md §10-5), D-E00110-04.

## 8. 📋 Caixa do Founder
1. **Implantar** `smith-api` → `smith-worker` → `portal-worker`. A flag continua desligada: nada muda no ar.
2. **O canário (G10)**: lataria na Yelum com apólice/veículo de teste e `PORTAL_CANARIO_ALLOWLIST` limitada ao job do ensaio. Só depois dele se liga a flag (D-E00110-F2).
3. **As capturas que faltam**, por valor, em `guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md` — a nº 1 é o **agendamento concluído**, até confirmar o horário.
4. **As 15 perguntas à atendente**, em `guias/PERGUNTAS-PARA-A-ATENDENTE-PORTAL-DE-VIDROS.md`; a nº 12 ("dá para retomar um atendimento parado?") **decide a 001.10.1**.
5. **Rotacionar as credenciais** coladas no chat de novo em 20/09 (reforça P-PILOTO-09).
6. **Decidir** D-E00110-F1 (contato do segurado), F2 (quando ligar a flag), F3 (a 001.10.1 antes da 001.8?).

## 9. Pendências e decisões
**Novas:** `P-E00110-A1…A18`, `C-03`, `C-05` e as **7 capturas** (agendamento concluído · vistoria/fotos · domicílio ·
`motivos-cancelamento` · questionário de vigia/farol/retrovisor/teto/para-choque · outra seguradora · outra corretora).
**Re-julgadas:** P-PILOTO-02 **PARCIAL** (run + `agent_id` + número durável + Ficha; falta o front da Fila) · P-PILOTO-07
**PARCIAL** (passo 7 lido e apresentado; agendar/fotos CANDIDATE) · P-PILOTO-08 **FECHADA no backend com prova** (G9; o leitor da
fila continua inexistente e já é pendência própria) · P-50 **CONTINUA** (por dado cobre as 38 na abertura; questionário só Yelum e
Porto). **Decisões:** `D-E00110-01…09` tomadas · `D-E00110-F1/F2/F3` 🧑 abertas — em `FOUNDER-DECISIONS.md`.

### 9.1 G11 — seguradora × estado (📊 `GET /seguradoras/`, HAR de 20/09: 38)

| slug | estado · evidência |
|---|---|
| LIBERTY | **provado ao vivo** — 3 HAR Yelum: lataria · para-brisa · vidro de porta |
| PORTO | **provado ao vivo** — 2 HAR: lanterna até o 80 % · roda sem cobertura |
| BRADESCO | **fora** — D-PILOTO-17: captura dupla antes de escrever |
| USEBENSNUBANK | **fora** — publicada como INATIVA no `NomeFantasia` |
| ALFA | construção · G3 |
| ALIRO | construção · G3 |
| ALLIANZ | construção · G3 |
| AXA | construção · G3 |
| AZUL | construção · G3 |
| BANESTES | construção · G3 |
| BB | construção · G3 |
| BPSEGURADORA | construção · G3 |
| BVIX | construção · G3 |
| CAIXA | construção · G3 |
| DARWIN | construção · G3 |
| GRINGO | construção · G3 |
| HDI | construção · G3 |
| INDIANA | construção · G3 |
| ITURAN | construção · G3 |
| JUSTOS | construção · G3 |
| MAPFRE | construção · G3 |
| MITSUI | construção · G3 · P-E00110-A15 (apelido × Toyota) |
| NEO | construção · G3 |
| PIER | construção · G3 |
| RPSADMINISTRADORA | construção · G3 |
| SANCOR | construção · G3 |
| SANTANDERAUTO | construção · G3 |
| SEMPARAR | construção · G3 |
| SERASA | construção · G3 |
| SOMPO | construção · G3 (`sompo`→GRUPO_HDI é rota de SPA) |
| SPLITRISK | construção · G3 |
| SULAMERICA | construção · G3 |
| TOKIOMARINE | construção · G3 |
| TOO | construção · G3 |
| TOYOTA | construção · G3 · P-E00110-A15 |
| USEBENS | construção · G3 |
| YOUSE | construção · G3 |
| ZURICH | construção · G3 |

**construção** = mesmo caminho de dado, sem captura própria; **G3** prova que cada uma resolve para o próprio slug.
**O que varia, medido:** o slug na chamada · `TipoAtendimento` (só a Porto manda `1`/`2`; a Yelum manda `null`) · itens cobertos e
motivos, que vêm **da apólice** · a regra do preflight (400 `RegraDeNegocioExcecao` na Porto sem cláusula). ❓ **Desconhecido:** o
questionário das 34 — se o portal perguntar algo nunca visto, o robô **PARA** com dossiê e a tela entra na fila de aprendizado (é o que G9 prova).

### 9.2 🔴 Nenhum motor paralelo foi criado (CLAUDE.md §5), item a item
**cliente HTTP** reusado (`SessaoVidros`, +17 métodos no mesmo objeto) · **guard/freio** estendido em `journeys/__init__.py` (o
novo é por job e só ESTREITA o global) · **máquina de estado** estendida (`vidros_estado.py`: a fronteira fixa virou função da
categoria) · **motor de questionário** estendido (`vidros_questionario.py`) · **tabela de perguntas** uma só
(`perguntas_do_portal_de_vidros.py`, +6 famílias) · **contrato à mão** não existe (o contrato A↔C é a SPEC §5, provado pelo teste
da costura) · **leitor de HAR** reusado (`trafego.importar_har`; `_replay_vidros.py` é fixture) · **vigia** estendido
(`app/tasks/vigia_do_portal.py`) · **tool** estendida (`portal_params`/`portal_tool`, nenhuma nova) · **seguradora**: 🔴 duas
tabelas MORRERAM (`_INSURER_ALIASES`, `SLUGS_DE_SEGURADORA`) e ficou a lista ao vivo + 1 tabela de apelidos.

## 10. Telemetria (§11) — `python scripts/medir_execucao_claude_code.py --sessao atual`
```
relógio total · por fase ........ 📊 20/09 22:53 → 21/09 03:18 UTC = 265 min no executor (faixa declarada 💭 10–14 h)
                                  leitores 18+6 ‖ · builders A 207 / C 54 · juiz 16 ‖ red team 16 · confirmação 10 · docs
turnos · contexto de pico ....... executor 60 · pico 366 k (teto 300 k estourado, §4) · builder A 360 · 788 k ·
                                  builder C 160 · 386 k · juiz 57 · 223 k · red team 47 · 276 k · confirmação 28 · 132 k
ctx-tokens · saída .............. agentes 266,4 M · saída 0,28 M · executor 16,3 M / 88 k · turnos somados 796
US$ API-equivalente ............. builder A 106,04 · C 23,95 · leitores 3,37+4,20 · juiz 5,55 · red team 5,54 ·
                                  confirmação 2,17 · docs 0,73 · executor 12,63 → total US$ 164,17
agentes além do executor ........ 8 de 24 (2 leitores · 2 builders · juiz · red team · confirmação · docs)
achados por mecanismo ........... costura A↔C 7 (EXCLUSIVOS) · juiz 4 (1 EXCLUSIVO: a regressão em produção) ·
                                  red team 7 (4 EXCLUSIVOS: peça, cidade, perímetro, agenda) · 3 achados pelos DOIS ·
                                  confirmação 2 (EXCLUSIVOS; 1 criado pelo conserto) · bateria 1 · canário: NÃO RODOU
rodadas da bateria .............. 1 inteira · 0 parciais (2 retriagens dirigidas isoladas depois do conserto)
nota da execução ................ 86/100 · juiz 74 → red team 55 → confirmação 84
```
**Nota da execução: 86/100** — critério: **3 HAR reais atravessados pelo motor** de ponta a ponta, mais a costura agente↔journey,
**20 mutações** vermelhas e **dois laudos independentes** consertados numa passada e confirmados por um juiz novo (84). Perde
pontos porque **o canário não rodou**, porque **a continuação não existe** — toda parada depois do protocolo ainda termina em mão
humana — e porque **uma regressão do próprio conserto** (cidade mutilada) só apareceu no juiz de confirmação, não nos gates.

## 11. Entrega
```
$ git rev-list --count HEAD..origin/main ; git rev-list --count origin/main..HEAD      # 📊 21/09/2026, antes
0
10
$ git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   083eeca..db49753  HEAD -> main
$ git fetch origin ; git rev-list --count HEAD..origin/main ; git rev-list --count origin/main..HEAD   # depois
0
0
$ git rev-parse --short HEAD ; git rev-parse --short origin/main
db49753
db49753
```
Antes do push, 📊 varredura do diff inteiro (`git diff 083eeca HEAD | grep -E "^\+" | grep -cE "sk-(proj|ant)|eyJhbGciOi|…"`):
**0** chaves/senhas; os 4 acertos no padrão de CPF são números sintéticos de teste; **0** arquivos de `docs/intake/` e **0** `.TXT`
do Founder no diff (o único `.txt` é `BATERIA-LINHA-DE-BASE.txt`, que é canon). O commit que fecha este relatório sobe em seguida.
**Implantar:** `smith-api` → `smith-worker` → `portal-worker`. **Variáveis novas:** `PORTAL_VIDROS_API_FIRST` (nasce
**desligada**; só o Founder liga, depois do canário) · `PORTAL_CANARIO_ALLOWLIST` (opcional; vazia = hoje; malformada = **barra
tudo**). Nenhuma variável existente mudou de significado; nenhuma migration; o caminho DOM continua atendendo em produção.

## 12. Handoff para a EXTRA-001.10.1 — a continuação
```
VERDE       a journey API-first vai do CPF ao desfecho sobre 3 HAR reais, atrás de flag; 38 seguradoras por dado; freio por
            job; work_run que a Fila enxerga; 26 paradas com número e sem promessa falsa; fila de aprendizado.
O BURACO    o token do portal vive SÓ EM MEMÓRIA (P-E00110-A11): toda parada depois da fronteira — agenda, vistoria, pergunta
            nova, erro do portal — termina em mão humana, mesmo com o número do atendimento na mão.
O QUE FALTA guardar o atendimento (número + o já respondido) de forma durável; reabrir pelo "Consultar atendimento"; concluir
            agenda/direcionamento quando as capturas existirem; a Fila ler o run (P-E00110-C-03).
DEPENDE DE  a captura nº 1 do roteiro (agendamento concluído) e a pergunta nº 12 à atendente ("dá para retomar por número?").
ONDE PAROU  main db49753 (último commit de código b246a4f), bateria na linha de base (35).
```
