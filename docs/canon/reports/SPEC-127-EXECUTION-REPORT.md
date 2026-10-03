# SPEC-127 — O portal de vidros no nível do WhatsApp

> Relatório de execução · 02–03/10/2026 · rito AAA v13 · 🔴 CRÍTICO · branch `spec/127-o-portal-de-vidros` · base `44e0f1a`
> (= a SPEC-126 inteira) · último código `7362725` (conserto único) · `6950353` = merge da `origin/main` (`0eb83d4`, a 126
> publicada) · SPEC `specs-propostas/SPEC-127-o-portal-de-vidros-no-nivel-do-whatsapp.md` · sessão `8fef6a21` (a mesma da 126).

## 0. O EXECUTION CARD (definitivo, ajustado ao que aconteceu)

```
OUTCOME ........  ENTREGUE COM RESSALVAS: nada abre no portal sem o resumo + o "ok" AMARRADO ao pedido (peça, cidade/UF
                  do serviço, final da placa); faltou dado → parada ANTES da escrita (0 POST) e a resposta volta ao MESMO
                  pedido (1 POST); cidade = a do SERVIÇO nos dois caminhos; reparo/ofertas/custo/"Não sabe" nunca
                  sozinhos; o DOM não escolhe peça/causa/lado; a parada chega ao destravador com a TELA.
                  📊 replay: 18/18 casos com dado faltando = 0 POST · cidade do cadastro 0/5 PATCH · DEDUZIR do portal = 0
RISCO ..........  8 (segurado e seguradora 3 · pedido aberto em sistema de terceiro 3 · todo pedido de vidro 2)
SUPERFÍCIE .....  3 (worker API-first e DOM, tool e portão do ok, destravador, vigia, bancada)
PISO APLICADO ..  §3.2 — escreve em sistema de TERCEIRO (portal da seguradora) → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · conserto único · confirmação
O FIO ..........  segurado pede vidro → portal_tool.portal_action (PORTÃO do ok + amarra ao pedido) → build_portal_params
                  (cadastro da corretora, cidade_servico) → job → worker abrir_atendimento → api_first → falta = parada
                  pré-fronteira etapa="abertura" → pergunta → resposta → vidros_continuacao (ramo abertura, MESMO pedido)
                  → POST /atendimentos (1) → … → desfecho
PARALELISMO ....  P1 (vidros_apifirst/estado/continuacao, portal_params) ‖ P2 (adaptive, perception, vidros_lanternas) →
                  P4+P8 (destravador + evidence) → P5 (módulo NOVO bancada_portal) → conserto único (série)
UNIDADES .......  BLOCO 0 · P1 · P2 · P4+P8 · P5 (gabarito, sem rodada) · conserto único. P6 = só a contenção dentro do
                  P2 (D-127-B); P7 adiada (D-127-A); P3 = canário do Founder (T-101)
COESÃO .........  "um portão do ok, uma régua do CEP, uma continuação por pedido"
TIME ...........  investigador BLOCO 0 · 3 builders · juiz ‖ red team · 1 builder de conserto · confirmação · atualizador.
                  A lente do dado prevista não rodou (a P5 não rodou paga)
REFERÊNCIA .....  interna: 6 HAR com abertura + 36 HTML do intake (caminho LOCAL), test_e001101_o_fio_da_continuacao,
                  test_spec124_portal_destrava_o_fio · externa: SPEC §7 (Anthropic agents/evals, Sierra ADLC, 2203.11171)
GATES ..........  G1–G8 (§4)
O ELO ..........  "chama pessoa PORQUE cai no DOM": B (queda None) 0 no replay depois do P1; mutação "a falta volta a
                  None" → o replay cai no DOM e 13 testes ficam vermelhos (B→A medido pela mutação)
FAIXA DE RELÓGIO  💭 1 dia (SPEC) · 📊 BLOCO 0 02/10 22:25Z → conserto 03/10 05:54Z ≈ 7 h 29 min, intercalada com a 126
nota da execução  87/100 (§11)
MIGRATIONS .....  nenhuma
ORÇAMENTO ......  📊 a 127 não gastou API: ledger `bancada` desde 02/10 18:50Z = OpenAI US$ 4,2796 (o mesmo da 126)
```
① Lentes: nenhuma (a do dado ficou para a rodada paga da P5). ② Auditoria: juiz ‖ red team cegos e a confirmação (§5).
③ Valor marginal: 📊 0 jobs de vidro desde 01/08 e 0 de 4 agentes de atendimento ligados → o replay dos HAR é a régua.

## 1. O QUE MUDOU (em linguagem clara)

- **BLOCO 0** corrigiu a SPEC antes de codar: o DOM tem **6** saídas para pessoa (não 5); o acervo tem 📊 **36 HTML** e **27 PNG**
  de tela (não 38/22) e **6 HAR com abertura** (o 7º, Porto roda sem cobertura, não abre); 📊 30 paradas em `ETAPA_DA_PARADA`;
  a lista "faltou" quase nunca chega ao worker (a tool já recusa antes); a consulta de atendimento já aberto só funciona
  DEPOIS do POST (precisa do token); 📊 1 de 3 corretoras com Perfil de Acionamento não tem documento; os jobs do DOM de julho
  levavam 📊 p90 210 s (> os 150 s da tool).
- **P2 (`1702b98`) — o DOM para de errar calado.** Preenche a cidade do **serviço** (autocomplete só aceita a cidade igual,
  nunca "Curitibanos" por "Curitiba"); reparo, ofertas e custo nunca são aceitos sozinhos; o rádio de cobertura da Porto é
  marcado pelo código; os cliques "Iniciar atendimento"/"Confirmar" passam pelo guarda da escrita; **contenção**: o modelo não
  escolhe peça, causa, perímetro, lado nem descrição — o DOM para e pergunta; só o que a tela pede vai ao modelo (token da URL
  mascarado). Achou e consertou 2 defeitos que travavam **todo** pedido pelo DOM (o validador e o "sem progresso").
- **P1 (`2253cf8`) — nenhum pedido de vidro sem o resumo + o ok** (o MESMO portão da SPEC-126). Faltou dado → parada antes da
  escrita, sem nada enviado; a resposta volta ao **mesmo** job e recomeça a abertura (1 POST). CEP do serviço no PATCH.
  Cadastro da corretora sem documento/telefone → a equipe é avisada, nada é perguntado ao segurado. A dedup do portal é
  consultada logo depois do POST, como a própria tela faz.
- **P5 gabarito (`672441f`, ANTES) + P4/P8/P5 (`d6b96f2`)** — o destravador do portal vê as paradas novas (a classe vem sempre
  da TABELA, nunca do modelo), lê a TELA (título, campo, rótulos, opções reais) e responde com o dado do caso quando o código
  prova (tipo de telefone, peça desambiguada por `especificos`). "Não sabe" nunca sai dele (P-124-07) e a regex do código da
  pergunta aceita `_`/`-` (P-124-15). Bancada do DEDUZIR do portal pronta, **não rodada** (orçamento) → autonomia = 0.
- **Conserto único (`7362725`)** — o "ok" ficou AMARRADO ao pedido: a pergunta tem de trazer a linha pronta, ou a peça + cidade
  + UF + final da placa DESTE pedido; o parente não vê a placa no aviso; uma continuação de abertura por pedido (nunca 2 POST);
  o DOM sem liberação para antes de consultar a apólice e não diz "a sua apólice cobre" (`pronto_para_iniciar`); o vigia
  respeita a tabela (não abre um 2º processo sobre a parada que o destravador conduziu); texto honesto à equipe ("abra DIRETO
  no portal, uma vez"); o CEP do cadastro só vai com a mesma cidade E UF, numa régua só para os dois caminhos.

## 2. COMMITS
📊 `git log --oneline 44e0f1a..6950353` (03/10) — 5 da SPEC-127, entremeados com os da 126 na mesma árvore:
`1702b98` P2 · `2253cf8` P1 · `672441f` gabarito P5 · `d6b96f2` P4+P8+P5 · `7362725` conserto único · + `6950353` merge.
📊 `git show --shortstat` dos 5 → +6.275 / −166; **33 arquivos** distintos, 9 `test_spec127_*`, novos `bancada_portal.py`,
`tests/corpus/bancada/portal/casos.jsonl` (📊 44 linhas), `fixtures/vidros/telas_dom.py` (mascarada), `_pagina_falsa_do_dom.py`,
`_arvore_do_html.py`. Nada fora de `backend/` (📊 `git show --name-only` dos 5, filtro `-notlike 'backend/*'` → 0).

## 3. BATERIA
(o gerente cola a contagem e a triagem)
Rodadas da bateria: 1 (suíte inteira em `C:\wt127`, depois do conserto, triada contra `BATERIA-LINHA-DE-BASE.txt`).
Antes dela: juiz `tests/test_spec127_*.py` 📊 **193 passed** (37,87 s) + regressão de replay (14 `test_e00110*`/`e001101*`
exit=0, `test_o_fio_do_portal_de_vidros` 66/0, 4 `test_spec074_*` exit=0, spec124/126 📊 143 passed); confirmação 📊 **115 passed**
(os 5 do pedido) e `test_e00110_a_escada_e_a_seguradora` 📊 166 verdes. `npm run test:rotas-montam`/`next start`: **não se aplica**
(📊 nenhum arquivo fora de `backend/`).

## 4. GATES
| gate | estado |
|---|---|
| **G1** replay, 0 POST com falta | ✅/🟡 📊 `scratchpad/p1_replay_tabela.py` (juiz): **18/18 casos com dado faltando = 0 POST**, cada um na parada certa (`faltou_cidade_servico`/`pedido_incompleto`/`cadastro_da_corretora_incompleto`), nenhum `None→DOM`; completos 1 POST. 🟡 "o completo chega ao desfecho do HAR": 📊 `done` em 2/6 (LAT, ANT); NOVO para em `decidir_reparo` (NUNCA, certo), PORTO em `questionario_incompleto`, LATARIA2 em `decidir_vistoria`, LATERAL em `faltou_onde` (o HAR traz perímetro "N", que a tool nunca monta). Mutação "a falta volta a None": juiz VERMELHO · red team **13 failed** |
| **G2** 0 cidade do cadastro | ✅ 📊 sonda C do juiz: PATCH com a cidade do SERVIÇO em **5/5 HAR com PATCH**, CEP do cadastro **0/5**; DOM `fatos_da_tela` = serviço, `so_igual=True`; sem `cidade_servico` → 0 fatos de lugar. Mutações: M3 (juiz) e D1 (red team, **1 failed**) vermelhas; Me "CEP aceita UF vazia" vermelha |
| **G3** nunca sozinho | ✅ DOM `plano_de_contencao`/`recusa_da_contencao`; destravador `_nao_sabe` + tabela (`decidir_oferta`/`decidir_reparo` NUNCA); o reparo só com `especificos.aceita_reparo`. Mutações declaradas: D3 oferta aceita sozinha **4 failed**, D2 autocomplete por prefixo **6 failed**, Mc "apólice cobre" vermelha. ⚠️ não houve uma mutação para CADA item (custo, cancelar, novo atendimento guardados por teste sem mutação própria) |
| **G4** 1 POST por pedido | 🟡 API-first ✅: a mesma resposta 2× → 1 job, 1 POST; 2 respostas DIFERENTES → 1 POST depois do conserto (📊 a sonda de corrida do juiz dava **2 POST**; Mb vermelha). DOM/R3: **não feito** (P7 adiada, D-127-A; as paradas do DOM vão à equipe) |
| **G5** destravador do portal | 🟡 replay MONTADO: 1 parada de cada tipo (conduzir · responder com dado · perguntar · deduzir calibrado) resolvida sem pessoa, 1 POST; classe sempre da TABELA (M4 vermelha); a guarda `test_C1_HOJE_…` migrou com controle (§9.3). ⚠️ red team: o "responder com dado" resolve 📊 **0/16** do gabarito real (seguro: viram pergunta) |
| **G6** DEDUZIR do portal | ✅ mecanismo · autonomia **0**. 📊 corpus 44 casos (yelum 33, 27 calibráveis · porto 11, 5 calibráveis < 10 → nunca religa); gabarito `672441f` antes de `d6b96f2`; **nenhuma rodada paga** (sobravam 💭 ≈ US$ 0,22; Yelum sozinha 💭 0,29–0,72). 📊 `cerebro_modos` on/false/40 (SELECT 03/10). "Curitibanos" nunca por "Curitiba" (teste) |
| **G7** ponte e 2 tenants | ⚪ **não se aplica**: a ponte HTTP não foi feita (D-127-B, nota 80 × 40); nenhum endpoint novo, `app/api/portal.py` intocado |
| **G8** bateria + replay + custo | (bateria: o gerente cola) · replay 001.10/001.10.1/124/074 verdes (§3) · §9.1 não se aplica · custo 📊 `token_usage_logs` `service_type='bancada'` desde 02/10 18:50Z (SELECT 03/10): `gpt-6-luna 2202 · 0,7878` + `gpt-6.1-sol 140 · 3,4918` = **OpenAI US$ 4,2796**, `claude-opus-5-5 1 · 0,0002` — igual ao fim da 126: a 127 gastou 0 |

## 5. JULGAMENTO — juiz ‖ red team → conserto → confirmação
- **Juiz (Opus 5.5 fresco, `d6b96f2`): APROVA COM 3 CONSERTOS, 80** — B1 o parente ouvia a placa inteira no aviso logo depois
  de confirmar uma linha sem placa; **B2** (exclusivo) duas respostas diferentes à mesma parada = 2 `POST /atendimentos`;
  **B3** (exclusivo) o DOM parado no passo 1 dizia "a sua apólice cobre" sem ter lido a apólice. 3 números 📊 reproduzidos
  (replay 18/18, corpus 44, a cidade 5/5); 4/4 mutações vermelhas com controle 📊 95 passed.
- **Red team (Opus 5.5, cego): QUEBREI, 72** (84 sem os dois) — **B1** (exclusivo) o "ok" não estava amarrado ao pedido:
  "abrir RETROVISOR em CURITIBANOS?" + "pode mandar" abria PARA-BRISA noutra cidade (📊 1 POST); B2 = juiz B1 (a placa).
  7 mutações próprias vermelhas, controles 📊 36/50 passed; só a da amarra sobreviveu.
- **Conserto único (`7362725`)** — os 5 blockers + as pendências RT-P1 (vigia × destravador), RT-P4 (duas réguas do CEP) e o texto
  à equipe (RT-P2).
- **Confirmação (`7362725`): CONFIRMA, 87** — as sondas ORIGINAIS rodadas de novo: amarra B/C → 0 job, controle A → 1 POST;
  placa ao parente `False`; a 2ª resposta cai no índice único; "cobre" no texto `False`; vigia `False`; CEP uma régua.
  📊 6 mutações (Ma–Mf) vermelhas, controle **154 passed**; **0 blocker novo**.

## 6. MIGRATIONS
**Nenhuma.** 📊 `git show --name-only` dos 5 commits → 0 arquivos em `backend/supabase/`. Nenhuma variável de ambiente nova;
as flags `PORTAL_VIDROS_API_FIRST`, `PORTAL_CANARIO_ALLOWLIST` e `PORTAL_EFEITO_MATERIAL_LIBERADO` seguem **ausentes** no
`.env` local (presença conferida pelos laudos). Nenhum pedido real no portal, nenhuma mensagem.

## 7. A DRENAGEM
| P | estado |
|---|---|
| P-124-07 | ✅ FECHADA — "Não sabe" nunca sai do destravador, nem calibrado; a regex de cancelar é UMA e reusa a do WhatsApp (`test_P124_07_*`) |
| P-124-15 | ✅ FECHADA — `pergunta_<codigo>` aceita `_`/`-`, com controle (`test_P124_15_*`) |
| P-126-22 | ✅ FECHADA — o `portal_action` passa pelo MESMO portão do ok (D-127-E), amarrado ao pedido (conserto) |
| P-124-01 | 🟡 CONTINUA — o DOM ganhou contenção e a parada leva a TELA; a ponte e a continuação do DOM viraram P-127-01/02/03 |
| P-124-02 | 🟡 CONTINUA — o mecanismo está pronto; a autonomia segue 0 → P-127-04 |
| P-124-08 | 🟡 CONTINUA — intocada; INFERÊNCIA: o CONDUZIR do tipo de telefone (P4) torna a espera aninhada alcançável com o API-first ligado |
| P-124-14 | ✅ já fechada na 126 (U6); o autocomplete do DOM agora também só aceita igual |
| P-123-01 | 🟡 CONTINUA — o n por seguradora (P-126-06, P-127-04) |

## 8. O QUE FICOU FORA
P-127-01…24 em `PENDENCIAS.md`: a ponte HTTP do DOM (P6) · a retomada R3 (P7) · as paradas do DOM sem continuação · a rodada
paga da P5 (e mais HAR da Porto) · cidade/UF validadas só depois do POST · o `PortalExecutionGateway` latente sem o portão ·
"responder com dado" 0/16 · peça uma resposta de cada vez · o matcher do questionário com chave alheia · lataria multipeça ·
`lxml` fora do requirements · o JS de captura do DOM e a SPA viva sem prova · a imagem da tela na parada · N1–N5 da
confirmação · "sim, mas é a lanterna" · a mesma amarra no `insurer_dispatch` · o canário com `cpf:` · a corretora sem
documento · o que ainda vai ao modelo do DOM · o `armed` sem `submitted` no vigia. O que a SPEC já tirava: o desfecho no DOM,
Bradesco ponta a ponta, o token que expira, as esperas encadeadas. Decisões D-127-A…G.

## 9. A CAIXA DO FOUNDER
`TAREFAS-DO-FOUNDER.md`, bloco S127 e **T-99 a T-103**: Implantar `smith-api` → `smith-worker` → `portal-worker` → `smith-web`
(nenhuma variável nova, nenhuma migration) · preencher o documento da corretora que falta (SQL só leitura mostra qual) ·
o canário do portal sobre o T-55/T-56 com a allowlist `cpf:` (o "ok" amarrado, a cidade do serviço, o parente) e como
desligar · decidir o orçamento da P5 · capturar ≥ 10 casos da Porto. Nada bloqueia: com as flags ausentes e 0 agentes
ligados, nada muda para o segurado até o canário.
**Desfazer:** tudo vive no código; o desfazer é voltar o código (*"reverta a SPEC-127 na main"*) e Implantar. Desligar o caminho
novo no ar: apagar `PORTAL_VIDROS_API_FIRST` do `portal-worker` e Implantar.

## 10. RISCOS REMANESCENTES (FATO · INFERÊNCIA)
- **FATO:** o DOM contido só foi provado contra páginas FALSAS geradas do HTML salvo; nada prova a SPA viva (Angular).
- **FATO:** a autonomia do portal é **0** — o DEDUZIR não religou (P5 sem rodada) e o "responder com dado" resolve 0/16 do gabarito.
- **FATO:** cidade/UF só são conferidas pelo portal DEPOIS do `POST /atendimentos` (📊 0 de 7 HAR mostram `/ufs`/`/cidades` sem
  token): uma cidade com erro abre o atendimento e para.
- **FATO:** o `PortalExecutionGateway` cria job sem o portão do ok se `PORTAL_EXECUTION_GATEWAY_MODE=on` (hoje ausente).
- **INFERÊNCIA:** com o português falado real, a amarra do ok pedirá UMA confirmação a mais em placa colada e "parabrisa" (N1) —
  o lado seguro (atrito, nunca escrita).
- **INFERÊNCIA:** a contenção pode transformar o DOM em "pessoa sempre" se o HTML vivo diferir do salvo; só o canário mede quantos
  pedidos o DOM contido ainda conclui.

## 11. NOTA E TELEMETRIA
**NOTA DO GERENTE: 87/100.** Critério: as 5 frases do Founder sobre o portal (nada abre sem o resumo + o ok; faltou dado →
pergunta antes e o MESMO pedido; a cidade do serviço; reparo/ofertas/custo nunca sozinhos; o DOM não escolhe sozinho) estão em
CÓDIGO, com teste pelo motor sobre os HAR e mutação vermelha. Perde por: DEDUZIR do portal = 0 (P5 sem orçamento); ponte e
retomada do DOM adiadas; DOM sem prova no portal vivo; canário pendente. Juiz 80 ‖ red team 72 → confirmação 87.

📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (03/10 ~06:15Z, sessão `8fef6a21`, 126 e 127 juntas;
trecho: o executor, os agentes da 127 e o total):
```
EXECUTOR (sessao principal)                  02/10 18:49    684 min  turnos  161  pico   501k  ctx   52.0M  saida   171k  US$   34.25  opus-5-5
  agente . BLOCO 0 investigation SPEC-127    02/10 22:25     23 min  turnos   83  pico   312k  ctx   16.5M  saida     6k  US$   10.09
  agente . SPEC-127 P1 API-first + gate      03/10 02:36     69 min  turnos  129  pico   482k  ctx   42.7M  saida    12k  US$   24.31
  agente . SPEC-127 P2 DOM containment       03/10 02:36     45 min  turnos  118  pico   434k  ctx   32.9M  saida     7k  US$   18.99
  agente . SPEC-127 P4+P8 then P5            03/10 03:45     64 min  turnos  133  pico   497k  ctx   40.5M  saida     6k  US$   23.15
  agente . Judge SPEC-127                    03/10 04:50     29 min  turnos   81  pico   290k  ctx   16.6M  saida     5k  US$    9.98
  agente . Red team SPEC-127                 03/10 04:50     23 min  turnos   73  pico   288k  ctx   13.4M  saida     6k  US$    8.40
  agente . SPEC-127 single fix pass          03/10 05:20     33 min  turnos   87  pico   302k  ctx   17.8M  saida     8k  US$   10.73
  agente . Confirmation judge SPEC-127 fix   03/10 05:55     16 min  turnos   27  pico   151k  ctx    3.1M  saida     4k  US$    2.37
  agente . Docs updater SPEC-127             03/10 06:13      1 min  turnos   12  pico   134k  ctx    1.1M  saida     0k  US$    1.23
TOTAL  agentes alem do executor: 34  .  turnos 3127  .  ctx 726.5M  .  saida 0.42M  .  US$ 431.34
```
Derivado (pela diferença ao relatório da 126, que leu US$ 392,88 no total e US$ 27,50 no executor): agentes da SPEC-127 ≈
**US$ 109,25** (9 agentes; o atualizador em curso) · executor (126 + 127) +US$ 6,75 desde então · total da sessão +US$ 38,46
(inclui o fim do atualizador e do conserto da bateria da 126). ⚠️ Os picos de 482k/497k dos builders P1 e P4 passam do teto
CRÍTICO de 300 k (§10) — declarado. APIs do produto: 📊 0 (G8). Achados por mecanismo: BLOCO 0 (6 correções da SPEC, entre
elas a lista "faltou" que quase nunca chega e a dedup só depois do POST) · prova mecânica (P2: 2 defeitos que travavam todo DOM)
· juiz 3 (B2, B3 exclusivos) · red team 2 (B1 exclusivo; a placa em comum) · confirmação 0 novos · bateria: (o gerente cola).
Nota do juiz 80 · red team 72 · confirmação 87.

## 12. ENTREGA
(o gerente cola a saída do push)

**Nenhum motor paralelo foi criado.** O portão do ok é o da SPEC-126 (`insurer_dispatch_tool.confirmacao_comprovada`,
importado, não reescrito); a continuação é a `vidros_continuacao` da 001.10.1 (ganhou o ramo "abertura"); a política das
paradas é o `destravador.py` da 123/124 (`CLASSE_DA_PARADA_DO_PORTAL`); a calibração é a de `cerebro_modos` (U6 da 126); a
bancada do portal é um módulo da `evals/` no molde de `bancada_confirmacao.py`; o vigia é o `vigia_do_portal` de sempre.
