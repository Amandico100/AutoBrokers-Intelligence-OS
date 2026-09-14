# Relatório de execução — SPEC-EXTRA-001.2: O agente lê tudo antes de falar

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `47bc8e3`

```
OUTCOME ..............  rajada de 5 mensagens + foto → UMA resposta (no máximo duas, e a segunda é continuação), sem
                        pergunta repetida, sem cumprimento no meio, com a identidade certa e o nome que a corretora escolheu
RISCO ................  8 = ALCANCE 3 (o SEGURADO) + REVERSIBILIDADE 3 (a mensagem SAI DO PRÉDIO; migration que altera ESTRUTURA
                        e TRAVA) + FREQUÊNCIA 2 (todo atendimento) — recontado: fica 8
SUPERFÍCIE ...........  3 — 📊 os 3 desvios de mídia confirmados (webhook.py:1452, :1637, :2228) + o provider da presença é OUTRO
                        arquivo do que a proposta previa (Evolution GO, não o Node) — "não consigo apontar todos" continua 3
PISO APLICADO ........  §3.2 três vezes: envia mensagem (e presença), migration que altera estrutura e trava, company_id na chave de
                        trava nova → CRÍTICO independente da conta
NÍVEL ................  CRÍTICO · laço curto (D-PILOTO-20; dossiê §7 "análise de qualidade AAA × laço curto"): builders Opus ·
                        juiz fresco Opus + 3 perguntas adversariais · lente do DADO. Sem aquecimento, sem 3 lentes, sem red team
UNIDADES .............  B0 medir · E migrations M1/M2 + uma conversa por contraparte + dedupe do pipeline + ordem do silêncio + feed ·
                        C a ficha sabe o que já foi respondido · AB trava de turno + janela por conteúdo + mídia no buffer +
                        re-planejamento + presença · DF apresentação/tamanho/identidade + o nome do agente
COESÃO ...............  A e B são UMA unidade (message_buffer_service + buffer_processor); D e F o mesmo hub (prompts.py +
                        o_fim_do_atendimento.py). Hubs com dono único: webhook.py · graph.py · o_fim_do_atendimento.py · buffer_processor.py
PARALELISMO REAL .....  onda 1: E ∥ C (arquivos disjuntos) · onda 2: AB · onda 3: DF. ≤ 2 builders ao mesmo tempo
TIME .................  orquestrador Fable · builders Opus 5 (E, C, AB, DF) · juiz fresco Opus 5 · lente do dado Opus 5 · conserto único
REFERÊNCIA ...........  interna: test_midia_e_concorrencia_do_webhook.py (linha de CONTROLE da trava) · test_a_ultima_palavra_humana_manda.py
                        (reencontro) · test_a_maquina_de_lavar_vai_ate_o_fim.py. externa: as 7 de §20 (Redis SET/locks · Meta typing ·
                        Evolution presence · Meta/Evolution webhooks · Stripe · "janela adaptativa não tem fonte")
GATES ................  G0 (G1c · G6 · G7 vermelhos hoje) + G1–G12 com mutação vermelha + M1/M2 VERIFY + canário + suíte + push
O ELO ................  "a resposta fragmenta PORQUE o debounce é por ociosidade": A medido (4 de 4 rajadas do piloto fragmentaram; 📊
                        no acervo 6.213 rajadas ≥3 respondidas: 83% com 2+ mensagens de resposta) · B medido (message_buffer_service.py:158
                        `max(…, 8)`; mídia desvia em 3 pontos) · B CHEGA em A ✅ (buffer_processor._uma faz get_and_clear e a varredura
                        de 1 s abre o 2º turno na chave nova)
FAIXA DE RELÓGIO .....  💭 6–9 h · real: em curso (início 14/09 ≈ 18:40 UTC)
ORÇAMENTO ............  💭 ≤ 1 M de subagentes (laço curto) · gasto: em curso
BLOCKER (o que é) ....  muda um byte do que o SEGURADO recebe, a atendente lê ou o banco guarda (protocolo §2)
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?            (preenche no fim)
② a AUDITORIA / juiz fresco? (preenche no fim)
③ pendências por VALOR MARGINAL: (preenche no fim)
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** proposta `docs/canon/specs-propostas/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md` (executada como está — D-PILOTO-20; o MODELO de abertura prevalece: laço curto)
**Branch:** `feat/extra-001-2-le-tudo-antes-de-falar`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 14/09/2026: `git fetch` · `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `47bc8e3` · árvore limpa)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (builders, juiz fresco, lente do dado)
**Início:** 14/09/2026
**Commit inicial:** `47bc8e3` (a main depois da EXTRA-001.1)
**Commit final:** (preenche no fim)
**Estado final:** EM EXECUÇÃO

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado: a trava de turno mora em `message_buffer_service` (mesmo Redis, mesma chave do buffer); a janela substitui a comparação de `should_process`; a ficha é `conversations.ficha_atendimento`; o feed é `log_activity`; a presença sai pelo provider Evolution GO que já existe; o índice único do espelho já existe (`20260806_02`).
- [ ] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada.
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo foi exposto (TESTE-A/TESTE-B por alias; o corpus de rajadas guarda só traços; o export com texto vive no scratchpad da sessão, fora do repositório).
- [ ] Nenhum escopo foi reduzido sem decisão registrada.
- [ ] Nenhum dado atravessou tenants.
- [x] `CLAUDE.md`, protocolo §0–§3/§5/§7.3, proposta inteira (1.146 linhas), research pack §3, D-PILOTO-02/07/08/12/14/20, `MIGRATIONS-AUTHORITY.md`, MODELO de abertura lidos no início.

## 0.1 O PROTOCOLO AAA — as duas contas, a referência e o laço

| unidade | ALC | REV | FREQ | RISCO | SUP | piso? | time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| E migrations + 1 conversa por contraparte + dedupe + silêncio/feed | 3 | 3 | 2 | 8 | 2 | migration altera ESTRUTURA e TRAVA | builder Opus · verificador · juiz + lente (VERIFY) |
| C ficha sabe o que já foi respondido | 3 | 2 | 2 | 7 | 1 | texto ao segurado | builder Opus · verificador · juiz |
| AB trava + janela + mídia + re-planejamento + presença | 3 | 3 | 2 | 8 | 3 | envia (e presença) | builder Opus · verificador · juiz + lente (corpus) |
| DF apresentação/tamanho/identidade + nome | 3 | 2 | 2 | 7 | 2 | texto ao segurado | builder Opus · verificador · juiz |

**Referência que o juiz abre:** `backend/tests/test_midia_e_concorrencia_do_webhook.py` (a linha de controle: conversas diferentes continuam paralelas) e `backend/tests/test_a_ultima_palavra_humana_manda.py` (o motor do reencontro).

**Telemetria (5 linhas, preenche no fim):** tokens do orquestrador · tokens dos subagentes · relógio · rodadas de bateria · nº de guardas/mutações.

---

## 1. BLOCO 0 — o que foi medido antes de qualquer código (14/09/2026, sobre `47bc8e3`)

### 1.1 Preflight (saída real)
```
git fetch origin                          (ok)
git rev-list --count HEAD..origin/main    0
git rev-list --count origin/main..HEAD    0
git branch --show-current                 feat/extra-001-2-le-tudo-antes-de-falar   (criada a partir de main = 47bc8e3)
git status --short                        (limpo)
```

### 1.2 A matriz `premissa → observação nova → comando/consulta → decisão`

| # | premissa da proposta (13/09, `a0bb5fe`) | observação de 14/09 (`47bc8e3`) | comando / consulta | decisão |
|---|---|---|---|---|
| 0 | 104 de 134 `wa_message_id` repetidos atravessam corretoras com papéis OPOSTOS (não é vazamento) | 📊 **157** repetidos · **0** na mesma conversa · **127** entre corretoras · **0 com o MESMO papel** nas duas pontas. 📊 `messages` 34.682, 33.348 com `wa_message_id` (96,2%) | consulta sobre `messages ⋈ conversations` | reconfirmado: as duas pontas da mesma conversa entre linhas das próprias corretoras; G9 nasce verde; nenhuma parada §10 |
| 3 | 3 desvios de mídia em `webhook.py` | ✅ **3**: `:1452`, `:1637`, `:2228` | `grep -n 'type": "media"'` | unidade B com os 3 pontos |
| 4 | `ROTULOS` 35 · `_SLOTS_DA_FICHA` 15 · 20 fora | ✅ **35 · 15 · 20**. 📊 `corridor_playbooks.py`: **20** `required_slots` distintos, **13 fora de ROTULOS** (`agua_escorrendo`, `vazamento_local`, `risco_confirmado_registro_fechado`, `caixas_dagua_quantidade_opcao`, `chaveiro_necessidade_opcao`, `qual_seguro_opcao`, `aparelho_marca/modelo`, `ar_condicionado_*`, `idade_aparelho_opcao`, `chave_tipo_opcao`, `caixa_litros_opcao`) | comando da §0.3 + AST dos playbooks | G6 vermelho hoje confirmado; `slots_do_atendimento()` deriva de `ROTULOS ∪ required_slots` |
| 5 | duração de um turno (para o TTL da trava): 💭 90 s | 📊 `conversation_logs.response_time_ms` (566 turnos; 276 de `attendance`): **p50 5,4 s · p90 17,9 s · máx 53,4 s** (attendance: 5,2 · 15,0 · 35,5) — é o tempo do modelo; o envio soma segundos | `percentile_cont` sobre `conversation_logs` | `TURNO_TTL_SEGUNDOS` = **90** (≈ 1,7× o máximo medido), 3 renovações — decisão D-E0012-01 |
| 6 | traços das mensagens reais medidos com a função do motor | ⚠️ `tracos_da_mensagem` ainda não existe (é do bloco B). 📊 O export de **400 rajadas** reais desde 01/08 (Resulta 159 · AutoFleet 241; tamanhos 2: 247 · 3: 92 · 4: 33 · 5+: 28; com mídia 96; **só mídia 35**) está no scratchpad da sessão com texto — o gerador do corpus roda a função do motor sobre ele e grava só traços | `psycopg` read-only sobre `attendance_transcripts.wa_timestamp` (nunca `messages.created_at`) | o gerador aceita `--de-arquivo` (export) e o banco; o corpus versionado não carrega texto |
| 7 | 20.727 rajadas · 72.610 msgs (85,6%) · 5.608 com mídia | 📊 hoje **20.834 · 72.933 (85,5% de 85.266) · 5.638 com mídia**; intervalos dentro da rajada: 0–3 s **31.052 (59,7%)** · 3–8 s 8.087 · 8–18 s 8.469 (16,3%) · 18–25 s 3.000 · >25 s 1.491 | a consulta do RP §3.1 sobre `wa_timestamp` | a janela por conteúdo continua justificada; 3 · 8 · 18 são o ponto de partida, calibrados pelo corpus no bloco B |
| 7b | (novo) como as respostas chegam depois de uma rajada ≥3 hoje | 📊 **6.213** rajadas ≥3 (≤60 s) com resposta: **1 mensagem 1.048 (17%) · 2 mensagens 2.741 (44%) · 3+ 2.424 (39%)**; mediana **92 chars** por bloco de resposta, p90 432; demora mediana 67 s; rajadas só de mídia ≥3: 298, das quais 27 respondidas com 1 mensagem. ⚠️ não separa agente de atendente humana (RP §3.9). Amostra redigida lida: respostas humanas são curtas e resolvem ("ok", "enviado", "oriente a aguardar 2h e fazer o pagamento") | consulta de blocos consecutivos por direção | régua do outcome: **1 resposta, no máximo 2**, curtas — é o que a humana faz |
| 8 | schema de `conversations`: `session_id` UNIQUE; `user_phone` sem índice; CHECK sem `fantasma_lid` | ✅ constraints e índices iguais aos da proposta; `ck_conversations_resolucao_motivo` = 5 valores sem `fantasma_lid`; 📊 **879** conversas (não 860); escritores da ficha: `nodes.py`, `human_handoff.py`, `acompanhamento.py` | catálogo | M1/M2 como propostas; `CONCURRENTLY` desnecessário |
| 9 | 175 fantasmas (106 AutoFleet · 69 Resulta), 100% abertas, 10 com pausa, 9 com par | 📊 dry-run do script (14/09): **175 fantasmas · 175 abertas · 69 Resulta + 106 AutoFleet · 10 com pausa humana (5+5) · cópia da pausa possível em 2 · 166 sem par**; `--vivo` recusado até a M1 (o próprio script imprime o APPLY/VERIFY) | `python scripts/migrar_conversas_fantasma_lid.py` (dry-run, saída redigida) | M1 destrava; **2** (não 9) têm par real ainda aberto — o número de hoje vence |
| 10 | 🔴 presença: existe `POST /chat/sendPresence/{instance}` no fork implantado? | 🔴 **DIVERGE (D1)**: o atendimento usa **Evolution GO** (D-E001-02), e o fork implantado expõe **`POST /message/presence`** com `{number, state, delay(ms), isAudio}` — o `delay` "mantém composing vivo re-enviando e manda paused ao fim" (swagger do GO, 83 rotas, 14/09); `/send/text` tem `delay`. Não existe `/chat/sendPresence` (é do Node) | swagger `doc.json` do GO implantado | a presença é VIÁVEL, pelo `EvolutionGoProvider._post` (evolution_go.py:441); flag `PRESENCA_DIGITANDO_LIGADA` nasce desligada |
| 11 | guardas que não podem quebrar, verde de partida | ✅ `test_midia_e_concorrencia_do_webhook` rc=0 · `test_a_ultima_palavra_humana_manda` 23 passed · `test_a_janela_esta_ligada_nos_portoes` 7 passed · `test_quem_fala_primeiro_cala_o_outro` rc=0 · `test_o_atendimento_tem_memoria` rc=0 | pytest / scripts | linha de controle registrada |
| 12 | nome do agente: `Amanda` desativada, `AutoBrokers` (core) ativo na Resulta; 0 colisões; `agent_enabled=false` em 5/5 | ✅ **confere** (8 agentes, 3 ativos, todos `core`; Resulta `Amanda` attendance inativa); 📊 colisão agente × membro **0** (10 membros ativos); ⚠️ `company_members.role` ∈ {`admin_company`, `member`} — **não existe papel `attendant`** (P-PILOTO-16) | SELECT | caixa do Founder (nome da Resulta); `atendente_de_plantao` regra (2) usa `member` não-owner — D-E0012-02 |
| 13 | silêncios sem motivo; `human_handoff_reason` em 6; 131 HUMAN_REQUESTED | 📊 `human_handoff_reason` **6**; HUMAN_REQUESTED **180** (era 131) | SELECT | bloco E: todo silêncio no feed |
| 14 | `max(settings.BUFFER…)` em 2 linhas | ✅ `:158` e `:166` | grep | morre no bloco B |
| 15 | integrações: nenhuma serve duas corretoras | ✅ 7 integrações · 3 corretoras · **0** `instance_id` compartilhado | SELECT | a chave `(escopo, telefone)` herda isolamento provado |
| 16 | linha de base da suíte | 📊 rodada da 001.1 (14/09, `3320cee`): **1107 passed · 18 failed · 48 errors** — as 18 triadas (harness P-088-MUT + pré-existentes) | relatório 001.1 §6.4 | reaproveitada |

### 1.3 Divergências (o número de hoje vence)

| id | divergência | consequência |
|---|---|---|
| **D1** | a presença sai pelo **Evolution GO** (`/message/presence`, `{number, state, delay, isAudio}`), não pelo Node (`/chat/sendPresence`) da proposta §6.4/§20 E03 | o bloco B implementa no `EvolutionGoProvider`; o `delay` do GO já renova e pausa sozinho; E03 vira referência de comportamento, não de rota |
| **D2** | 2 fantasmas com par real ainda aberto (não 9); 10 com pausa presa (o script conta 5+5) | o `--vivo` copia 2 pausas e fecha 175 |
| **D3** | `company_members.role` não tem `attendant`; só `admin_company`/`member` | `atendente_de_plantao` regra (2) = exatamente um `member` ativo não-owner; senão `None` |
| **D4** | 879 conversas (não 860); 180 HUMAN_REQUESTED (não 131); 157 ids repetidos (não 134), 0 com o mesmo papel | números de hoje no relatório; G9 invariante correta |
| **D5** | `tracos_da_mensagem` não existe antes do bloco B: o item 6 do BLOCO 0 é feito pelo gerador do corpus sobre o export real (400 rajadas) | o corpus é gerado no bloco B, com a função do motor, sobre texto real; o relatório cola as contagens |

---

## 2. BLOCO E — (preenche ao fechar)

## 3. BLOCO C — (preenche ao fechar)

## 4. BLOCO AB — (preenche ao fechar)

## 5. BLOCO DF — (preenche ao fechar)

## 6. Migrations (APPLY / VERIFY / ROLLBACK)

## 7. Painel: juiz fresco + lente do dado · conserto · suíte

## 8. Canário (depois do Implantar)

## 9. O que ficou fora e por quê

## 10. Decisões tomadas com nota

| id | decisão | opções e notas | por quê |
|---|---|---|---|
| **D-E0012-01** | `TURNO_TTL_SEGUNDOS` = 90, 3 renovações | 90 **85** · 60 **55** (máx medido 53 s + envio) · 180 **40** (trava órfã longa) | premissa 5 |
| **D-E0012-02** | `atendente_de_plantao` regra (2) usa `company_members.role='member'` ativo e não-owner (não existe `attendant`) | member **80** · criar papel `attendant` agora **25** (P-PILOTO-16 é decisão 🧑) | D3 |

## 11. Riscos remanescentes

## 12. Rollback

## 13. Entrega (`git push`, saída colada)
