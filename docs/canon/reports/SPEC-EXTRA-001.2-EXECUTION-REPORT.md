# Relatório de execução — SPEC-EXTRA-001.2: O agente lê tudo antes de falar

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `47bc8e3`

```
OUTCOME ..............  rajada de 5 mensagens + foto → UMA resposta (no máximo duas, e a segunda é continuação), sem
                        pergunta repetida, sem cumprimento no meio, com a identidade certa e o nome que a corretora escolheu
RISCO ................  8 = ALCANCE 3 (o SEGURADO) + REVERSIBILIDADE 3 (a mensagem SAI DO PRÉDIO; migration de ESTRUTURA e TRAVA)
                        + FREQUÊNCIA 2 (todo atendimento) — recontado: 8
SUPERFÍCIE ...........  3 — 📊 os 3 desvios de mídia confirmados (webhook.py:1452, :1637, :2228) + o provider da presença é OUTRO
                        arquivo do que a proposta previa (Evolution GO, não o Node) — "não consigo apontar todos" continua 3
PISO APLICADO ........  §3.2 três vezes: envia mensagem (e presença), migration de estrutura e trava, company_id na chave nova
                        → CRÍTICO independente da conta
NÍVEL ................  CRÍTICO · laço curto (D-PILOTO-20; dossiê §7 "análise de qualidade AAA × laço curto"): builders Opus ·
                        juiz fresco Opus + 3 perguntas adversariais · lente do DADO. Sem aquecimento, sem 3 lentes, sem red team
UNIDADES .............  B0 medir · E migrations M1/M2 + uma conversa por contraparte + dedupe do pipeline + ordem do silêncio + feed ·
                        C a ficha sabe o que já foi respondido · AB trava de turno + janela por conteúdo + mídia no buffer +
                        re-planejamento + presença · DF apresentação/tamanho/identidade + o nome do agente
COESÃO ...............  A e B são UMA unidade (message_buffer_service + buffer_processor); D e F o mesmo hub (prompts.py +
                        o_fim_do_atendimento.py). Hubs com dono único: webhook.py · graph.py · o_fim_do_atendimento.py · buffer_processor.py
PARALELISMO REAL .....  onda 1: E ∥ C (arquivos disjuntos) · onda 2: AB · onda 3: DF. ≤ 2 builders ao mesmo tempo
TIME .................  orquestrador Fable · builders Opus 5 (E, C, AB, DF) · juiz fresco Opus 5 · lente do dado Opus 5 · conserto único
REFERÊNCIA ...........  interna: test_midia_e_concorrencia_do_webhook.py (CONTROLE da trava) · test_a_ultima_palavra_humana_manda.py ·
                        test_a_maquina_de_lavar_vai_ate_o_fim.py. externa: as 7 de §20 (Redis locks · Meta typing · Evolution presence ·
                        webhooks · Stripe · "janela adaptativa não tem fonte")
GATES ................  G0 (G1c · G6 · G7 vermelhos hoje) + G1–G12 com mutação vermelha + M1/M2 VERIFY + canário + suíte + push
O ELO ................  "a resposta fragmenta PORQUE o debounce é por ociosidade": A medido (4/4 rajadas do piloto; 📊 acervo: 83%
                        das 6.213 rajadas ≥3 com 2+ respostas) · B medido (`max(…, 8)` em message_buffer_service.py:158; mídia desvia
                        em 3 pontos) · B CHEGA em A ✅ (_uma faz get_and_clear; a varredura de 1 s abre o 2º turno na chave nova)
FAIXA DE RELÓGIO .....  💭 6–9 h · real: ≈ 8 h numa janela (14/09 18:40 → 15/09 ≈ 02:40 UTC), sem queda
ORÇAMENTO ............  💭 ≤ 1 M de subagentes (laço curto) · 📊 gasto: ≈ 1,45 M (E 394k · C 253k · AB 294k · DF 289k · juiz 199k · lente 146k · conserto 317k) — acima do teto: 7 subagentes em vez de 5
BLOCKER (o que é) ....  muda um byte do que o SEGURADO recebe, a atendente lê ou o banco guarda (protocolo §2)
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?            SIM — laço curto: juiz fresco Opus (3 perguntas fixas + 10 achados, nota 62) ∥ lente do dado Opus
                             (11 reconstruções sobre o acervo real, 88) → conserto único (9/9 com guarda vermelho)
② a AUDITORIA / juiz fresco? SIM — 2 BLOCKERs (J1 janela 18 s padrão; J2 rajada perdida no turno vencido), 2 ALTOs, 5 MÉDIOS,
                             1 BAIXO; os 9 de produto consertados; J10 virou pendência
③ pendências por VALOR MARGINAL: 21 abertas (4 do E, 4 do C, 3 do AB, 3 do DF, 6 do conserto, 1 🧑 nome) — nenhuma muda um byte
                             do que o segurado recebe HOJE; as 2 que mais valem: P-E0012-J11 (posse real da trava, canário) e
                             P-E0012-D1 (memória com nome antigo)
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** proposta `docs/canon/specs-propostas/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md` (executada como está — D-PILOTO-20; o MODELO de abertura prevalece: laço curto)
**Branch:** `feat/extra-001-2-le-tudo-antes-de-falar`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 14/09/2026: `git fetch` · `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `47bc8e3` · árvore limpa)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (builders, juiz fresco, lente do dado)
**Início:** 14/09/2026
**Commit inicial:** `47bc8e3` (a main depois da EXTRA-001.1)
**Commit final:** o commit que fecha este relatório (`docs(extra-001.2): fechamento`) — o hash da `main` está no §13 e em `ESTADO-DAS-SPECS.md`
**Estado final:** ✅ **CONCLUÍDA COM RESSALVAS** — código na `main`; 2 migrations aplicadas; canário dos 8 casos e validação com as atendentes dependem do Implantar (🧑). **Nota do orquestrador: 85/100** — critério: 100 = os 12 itens da §23 no ar E provados no canário vivo; desconto por canário não rodado (−8), pela decisão de 94 que o painel derrubou (a janela; −4) e pelas 3 pendências que o código só desaconselha (memória, corrida do espelho, posse real; −3)

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
| 7 | 20.727 rajadas · 72.610 msgs (85,6%) · 5.608 com mídia | 📊 hoje **20.834 · 72.933 (85,5% de 85.266) · 5.638 com mídia**; intervalos dentro da rajada: 0–3 s **31.052 (59,7% com `<=3`; 🔴 lente: com o operador do MOTOR, `gap<3`, são 29.113 = 55,8%** — a faixa de borda estava do lado errado; o RESEARCH-PACK tinha 56,0%) · 3–8 s 8.087 · 8–18 s 8.469 (16,3%) · 18–25 s 3.000 · >25 s 1.491 | a consulta do RP §3.1 sobre `wa_timestamp` | a janela por conteúdo continua justificada; 3 · 8 · 18 são o ponto de partida, calibrados pelo corpus no bloco B |
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

## 2. BLOCO E — uma conversa, uma linha, e todo silêncio com motivo (Builder E · Opus 5 · 📊 394k tokens · ≈3 h)

| entrega | o que mudou | prova |
|---|---|---|
| E.1 dedupe do pipeline | escritor ÚNICO de `messages` no pipeline (`gravar_mensagem_do_pipeline`) com `payload = {wa_message_id, origem: "agente", direcao}` e 23505 = sucesso silencioso. 📊 D-E-1: `whatsapp_service.send_message` devolve `bool` e fatia em balões — o id do provider NÃO atravessa a fachada; a linha da IA é gravada ANTES do envio, sem chave (declarado; a rede continua `e_a_nossa_propria_voz` + `_eco_do_dashboard`) → **P-E0012-02** | `test_uma_entrega_uma_linha_um_turno.py` **18/18**: a mesma entrega 2× pela rota real → 1 linha e 1 turno; a invariante CORRETA de tenant (nenhum grupo com o MESMO papel sob dois `company_id`; a ingênua é falsa por construção); 3/3 mutações vermelhas |
| E.2 uma conversa por contraparte | `contraparte_de()` pura (delega a `telefone_do_evento`); os 2 resolvedores (webhook e espelho) buscam por `(company_id, contraparte, whatsapp, sem agente, aberta)` antes de criar e gravam a coluna; **M2** coluna + backfill + índice único parcial; **M1** CHECK com `fantasma_lid` + `MOTIVOS` | `test_uma_conversa_por_contraparte.py` **30/30**: `@lid` com alternativo e telefone → mesma chave; 2ª aberta recusada; PAR outra corretora aceita; fechada não bloqueia; 4/4 mutações vermelhas |
| E.3 o silêncio | ordem `company_id → pausar_ia → exceção (só para a janela) → janela`; docstring de 4 passos; P-PILOTO-15 pela opção (b′): a pausa protege quando `claimed_at > resolvido_em` (D-E0012-03: 88 × limpar `resolvido_em` 35 — 📊 12 leitores do campo — × ingênua 40); `anotar_silencio_no_feed` sem o filtro `foi_a_janela`, escrito DENTRO de `a_ia_deve_calar` (D-E-3), memo por conversa/CLASSE/dia (a frase do takeover carrega nome — D-E-6); a não-calada por exceção vira linha; 📊 D-E-4: "sem corretora" NÃO produz linha (o feed escreve por `company_id`) — são 4 motivos com linha, não 5 | `test_todo_silencio_tem_motivo.py` **48/48**: exceção NÃO fura o takeover; 4 motivos → 4 linhas em português; 1 linha por conversa/classe/dia; conversa reaberta com atendente dentro → protegida; 4/4 mutações vermelhas |
| E.4 `.env.example` | `BUFFER_*` 3/30/300 → 8/25/60 (o exemplo mentia sobre `config.py`) | leitura |

Testes existentes migrados sob §9.3: `test_o_espelho_vira_conversa`, `test_quem_fala_primeiro_cala_o_outro` (carregam `identidade_do_evento` REAL; `contraparte` no whitelist do dublê) e — pelo orquestrador — `test_o_atendimento_termina_e_o_produto_sabe` (lê a lista do CHECK da migration que a define hoje: 6 motivos; 52 passed). 🔴 Defeito de arnês achado: `subprocess.run(text=True)` decodifica em cp1252 no Windows e estoura no 1º emoji — uma mutação VERMELHA era contada como verde; os arnês passam `encoding="utf-8", errors="replace"` (vale para todo guarda novo). Conferido pelo orquestrador: 18 + 30 + 48 verdes; 4/4 mutações do G11 vermelhas; espelho ×3 e portões verdes.

## 3. BLOCO C — a ficha sabe o que já foi respondido (Builder C · Opus 5 · 📊 253k tokens · ≈2h15)

| entrega | o que mudou | prova |
|---|---|---|
| C.1 o escritor deixa de ser lista à mão | `slots_do_atendimento()` = `ROTULOS ∪ required_slots` dos playbooks (lidos pelo MOTOR, não por regex — 📊 **54** `required_slots` distintos, **37** fora de `ROTULOS` ANTES do bloco (hoje `required_slots − ROTULOS` = **0**, porque o C.1 acrescentou os 37), não 20/13: metade dos subserviços nasce em tempo de importação — divergência D6) − `CAMPOS_DE_CONTROLE = {dados_confirmados}` (D-E0012-04: 90); +37 rótulos em português; a tupla `_SLOTS_DA_FICHA` MORREU | `test_todo_slot_do_corredor_tem_ficha.py` **11/11** (🔴 vermelho de partida colado no docstring: `ImportError`, "o escritor gravou só problema_descricao/titular_cpf"); 3/3 mutações vermelhas |
| C.2 origem por confirmação | `confirmados[slot] = {valor, origem ∈ cliente/sistema_de_gestao/corredor, em}` com leitura tolerante ao valor cru (D-E0012-05: 92); origem `sistema_de_gestao` só para placa/veículo quando há contexto InfoCap; o bloco do prompt separa "JÁ CONFIRMADO com o cliente — não pergunte" de "veio do sistema de gestão — confirme numa frase"; `dados_conhecidos` desembrulha (sem isso a URA receberia o dict como placa) | idem |
| C.3 pergunta repetida | `slots_reperguntados(resposta, ficha, corredor)` pura sobre `ancoras_de_pergunta_por_slot.json` (72 slots, 56 com âncora, **16 sem** — 12 são pedaços de endereço perguntados em bloco → P-E0012-C3), no dialeto de `corridor_playbooks._norm` (IGNORECASE|DOTALL, com acento+negrito); em produção, o fiscal em `agent_node` regenera UMA vez com a lista e depois envia e registra `pergunta_repetida` em `log_activity` | `test_slot_confirmado_nao_se_pergunta.py` **21/21**: replay estrutural do encanador (`agua_escorrendo` confirmado → não volta); 3/3 mutações vermelhas |

Divergências: D6 (54/37); D7 🔴 existe um SEGUNDO vocabulário (`corridor_playbooks._COMO_PERGUNTAR`, ~60 redações) — a docstring de `ROTULOS` ("o ÚNICO") era falsa; G6 é a trava que fica vermelha se divergirem → **P-E0012-C2**. Os 3 escritores da coluna são donos de chaves disjuntas (confirmado). Conferido pelo orquestrador: 11 + 21 verdes; 6/6 mutações; `test_o_atendimento_tem_memoria` (promovido para o motor) e `test_a_maquina_de_lavar_vai_ate_o_fim` (112) verdes.

## 4. BLOCO AB — a trava de turno, a janela por conteúdo, a mídia no buffer e o "digitando" (Builder AB · Opus 5 · commit `56d8bb3`)

| entrega | o que mudou | prova |
|---|---|---|
| A.1 trava de turno | `whatsapp_turno:{escopo}:{phone}` por `SET NX EX` com token `uuid4`; `renovar_turno`/`fechar_turno` por Lua CAS (só o dono solta); `TURNO_TTL_SEGUNDOS=90` (📊 p90 18 s · max 53 s — BLOCO 0), `TURNO_RENOVACOES_MAX=3`; o turno abre ANTES do `get_and_clear` em `processar_buffers_prontos_uma` e fecha no `finally`; escopo vazio → recusa fail-closed (D-E0012-08); reconferência de posse (`ainda_sou_o_dono`) antes de cada envio | `test_uma_rajada_um_turno.py` **60/60**: 2 processadores sobre a mesma rajada → 1 turno; rajada de 5 pelo corpus real → 1 resposta; TTL vence no meio → o segundo não envia; 9/9 mutações vermelhas (inclui `max(settings.BUFFER` de volta) |
| A.2 janela por conteúdo | `tracos_da_mensagem` (dado curto · frase completa · frase inacabada · identificador placa/CPF) → `janela_de_espera` 3 · 8 · 18 s, `TETO_DA_RAJADA_SEGUNDOS=25`; o teto só DESCE (uma frase completa depois de uma inacabada encurta a espera, nunca alonga); o piso `max(settings.BUFFER_*, 8)` morreu — 📊 `grep "max(settings.BUFFER"` no produto = **0** (as 2 ocorrências restantes são o alvo da mutação no guarda) | idem; corpus: 📊 sobre as **400** rajadas do acervo (1.059 itens, **892 de texto** — as contagens abaixo são sobre texto): pontuação final **235**, conectivo no fim **22**, dado curto **60**; a janela adaptativa fragmentaria **203** rajadas × a fixa de 8 s **273** (📊 lida no scratchpad, script `gerar_corpus_de_rajadas.py`) |
| B.1 mídia no buffer | os 3 desvios de mídia do webhook morreram (`grep 'type": "media"'` = **0**); `_item_do_inbound` põe imagem/áudio/documento como item tipado no buffer v2 (`itens`, leitura tolerante ao v1); visão/transcrição rodam DENTRO do turno (`_midia_do_turno`), não no recebimento | `test_a_midia_entra_no_buffer.py` **23/23**: 10 imagens em 20 s → 1 turno, 1 resposta; imagem + legenda + texto → um só contexto; 5/5 mutações vermelhas |
| B.2 re-planejamento | o que chegou durante o turno é mesclado ANTES de gravar e gerar (`mesclar_o_que_chegou`, `REPLANEJAMENTOS_MAX=2`); passado o teto, o resto fica para o próximo turno | idem |
| B.3 presença | `send_presence` na fachada e no `EvolutionGoProvider` (`POST /message/presence`, teto 25 000 ms — 📊 rota confirmada no swagger do fork, D1); só DEPOIS do portão de silêncio (`a_ia_deve_calar`) e atrás de `PRESENCA_DIGITANDO_LIGADA` (default **false** — 🧑 liga depois do canário); sem `delay` no `/send/text` | `test_digitando_so_quando_vai_falar.py` **30/30**: calada → nenhuma presença; ligada e vai falar → 1 presença antes do texto; provider sem `presence` → nada; 5/5 mutações vermelhas |
| corpus | `tests/corpus/rajadas_reais.jsonl` — **20** rajadas reais SÓ com traços (tipo, tamanho, gap, traços; 📊 0 acertos de PII no scan: A **11** · B **9**, **6** com mídia, **17** viram 1 turno na simulação) + `rajadas_reais.INDICE.md` | leitura + os 3 guardas replicam sobre ele |

Env novas (7, nomes; valores de exemplo em `.env.example`): `TURNO_TTL_SEGUNDOS`, `TURNO_RENOVACOES_MAX`, `JANELA_DADO_CURTO_SEGUNDOS`, `JANELA_FRASE_COMPLETA_SEGUNDOS`, `JANELA_FRASE_INACABADA_SEGUNDOS`, `PRESENCA_DIGITANDO_LIGADA`, `REPLANEJAMENTOS_MAX` — nenhuma obrigatória (todas com default no `config.py`). Conferido pelo orquestrador (saída real): 60 + 23 + 30 verdes; controles `test_midia_e_concorrencia_do_webhook` rc=0, `test_a_maquina_de_lavar_vai_ate_o_fim` 112, `test_uma_entrega_uma_linha_um_turno` 18, `test_todo_silencio_tem_motivo` 48, `test_higiene_de_plataforma` rc=0; 19/19 mutações vermelhas. 🔴 O arnês de mutação decodifica em utf-8 (lição do E).

## 5. BLOCO DF — a apresentação, o tamanho, a identidade da thread e o nome (Builder DF · Opus 5 · 📊 ≈215k tokens · ≈1h50 · commit `c77f81c`)

| entrega | o que mudou | prova |
|---|---|---|
| D.1 apresentação | `deve_se_apresentar(assunto_novo, apresentado_neste_assunto, nome_atual, nome_da_apresentacao)` pura ao lado do reencontro → uma de 3 linhas no bloco DINÂMICO (primeira · "não se apresente" · "mudou de nome, diga uma vez"); o `SEMPRE se apresente` morreu (📊 `grep` no fonte = **0** e no prompt montado = 0); o bloco de identidade **não some mais** com nome vazio ("assistente virtual da {corretora}") | `test_o_agente_se_apresenta_uma_vez.py` **42/42**: replay estrutural do encanador (30 turnos) → **1** apresentação, na abertura; assunto novo → 1; troca de nome → nada agora, uma linha no seguinte; 6/6 mutações vermelhas (`SEMPRE` de volta · sempre True · herdar identidade · teto de frases 99 · teto de chars 9999 · sem regeneração) |
| D.2 tamanho | `classe_do_tamanho` + `TETO_POR_CLASSE` (conversa 3 · bloco 4 · lista 0 · avisar 1) **e** `CHARS_POR_CLASSE[conversa]=450` (📊 p90 = 432 do acervo; a proposta só contava frases — D-E0012-13); 4º fiscal `_resposta_no_tamanho_da_classe` em `agent_node` (depois do de pergunta repetida): UMA regeneração com a régua, depois envia e registra `tamanho_fora_da_classe`; balões (300/500/4) continuam humanização | idem: conversa de 644 chars em 3 frases → fora → regenera → envia e registra; lista de 20 itens → sem teto (PAR) |
| D.3 identidade da thread | `ficha["identidade"] = {assunto_id, titular_nome, apresentado_em, nome_da_apresentacao}`; `fundir` ganha a ÚNICA exceção à aditividade: assunto novo derruba `SLOTS_DA_IDENTIDADE`; o reencontro passou a ser calculado ANTES da ficha em `graph.py`; 📊 a única porta nomeada do nome do titular era `ROTULOS["titular_nome"]` → fechada; o bloco "QUEM FALA NESTE TURNO" é o ÚLTIMO do `dynamic_context` e desaconselha nomes vindos da memória (⚠️ porta que o código NÃO fecha: `=== 🧠 MEMÓRIA ===` por `user_id` → **P-E0012-D1**) | idem: o nome de 22 dias atrás não volta no assunto novo |
| F.1 o nome | `atendente_de_plantao(company_id, membros, plantao=None)`: (1) plantão (parâmetro; a 001.3 liga) · (2) exatamente **um** `member` ativo não-owner · (3) `None` → "Vou passar seu caso para a nossa equipe…" — nunca o agente; 🔴 D-DF-c: `prompts.py` ENSINAVA nomes inventados ("a Ana", "o Marcos", "o analista") em 3 das 5 formas de handoff — removidos | `test_o_nome_do_agente_nao_confunde.py` **33/33**: duas corretoras no mesmo teste, cada prompt com o seu nome; 1 member → nome; 2 → None; 0 → None; a copy nunca contém `agent_name` |
| F.2 recusa no servidor | 📊 quem grava `attendant_name` é `PATCH /api/dashboard/agents/[agentKey]` → `patchTenantAgentConfig` (`lib/admin/tenant-agent-store.ts`), não o FastAPI (D-E0012-14); `colisao_com_a_equipe` normalizada (acento/caixa/espaços; nome completo e primeiro nome) contra `company_members` ativos da MESMA corretora → `400` + frase; legado colidente (📊 0 hoje) só avisa; o card mostra as duas frases | idem: a rota real transpilada com o `typescript` do repo sobre dublê de Supabase (blueprints e `tenant-overview-store` reais) recusa colisão e aceita nome livre; membro da corretora B não bloqueia a A; 4/4 mutações vermelhas |
| F.3 assinatura | dossiê/grupo: `🤖 {agent_name}` no agente, a pessoa pelo nome SEM emoji (`👤` saiu — dois emojis apagavam a distinção) | idem |

Testes existentes: `test_a_ultima_palavra_humana_manda.py` **26** (eram 23; +3 casos do `deve_se_apresentar` integrado ao `bloco_do_reencontro`); `test_o_atendimento_tem_memoria` rc=0; `test_a_maquina_de_lavar_vai_ate_o_fim` 112; `test_slot_confirmado_nao_se_pergunta` 21; `test_todo_slot_do_corredor_tem_ficha` 11; handoff (3 guardas) verdes; `npm run test:rotas-montam` → **301 rotas ordenadas**; `tsc --noEmit` 0 erros. Conferido pelo orquestrador (saída real): 42 + 33 verdes; 10/10 mutações vermelhas; `grep "SEMPRE se apresente"` = 0; os 6 guardas dos blocos anteriores continuam verdes (60/23/30/112/21/48); rotas montam.

## 6. Migrations (APPLY / VERIFY / ROLLBACK) — as duas, aplicadas em 14/09/2026 (MCP), MANIFEST atualizado

### `20260914_07_spec_extra001_2_check_fantasma_lid.sql` (M1)
| Campo | Conteúdo |
|---|---|
| **Objetivo** | `ck_conversations_resolucao_motivo` aceita `fantasma_lid` (destrava P-PILOTO-13) |
| **Destrutiva** | não (a lista só cresce); expand-first |
| **VERIFY (saída real)** | V1 `pg_get_constraintdef` contém `fantasma_lid` → **true** · V2 UPDATE com motivo fora da lista → **RECUSADO 23514**; com `fantasma_lid` → **ACEITO** (revertido) · V3 linhas com `fantasma_lid` → **175** · V4 fantasmas ainda abertas → **0** |
| **`--vivo`** | `migrar_conversas_fantasma_lid.py --vivo` (14/09): **2 pausas copiadas · 175 fantasmas fechadas · 0 falhas · VERIFY do script = 0** (dry-run antes: 175 · 69 Resulta + 106 AutoFleet · 10 com pausa · 166 sem par). ⛔ Nenhuma mensagem apagada; não é o encerramento em lote da D-PILOTO-02 (são LIDs sem telefone) |
| **ROLLBACK** | escrito; RECUSA reverter enquanto houver linhas com `fantasma_lid` (reverter deixaria 175 `closed` sem motivo, violando o CHECK de coerência) |

### `20260914_08_spec_extra001_2_contraparte_unica.sql` (M2)
| Campo | Conteúdo |
|---|---|
| **Objetivo** | `conversations.contraparte` (só dígitos do telefone; `@lid` cru → NULL) + índice único parcial `uq_conversations_contraparte_aberta (company_id, contraparte) WHERE whatsapp AND agent_id IS NULL AND status <> 'closed' AND contraparte IS NOT NULL` — impede a fantasma nº 176 |
| **Ordem seguida** | (a)+(b) coluna + backfill → **D0 duplicatas abertas = 0** → (c) índice (D-E0012-06: índice só com D0 = 0 — 92; fechar a mais antiga em lote 20) |
| **VERIFY (saída real)** | V1 `indexdef` com as 4 cláusulas ✅ · V1b CONTROLE fantasmas sem chave = **171** (> 0: a recusa do LID rodou) · V2 duplicatas abertas = **0** · V3 2ª aberta da mesma contraparte → **RECUSADO 23505** · V4 outra corretora, mesma contraparte → **ACEITO** (o PAR) · V5 fechada → **ACEITO**; linhas de VERIFY apagadas (0 sobras; 879 conversas) |
| **Advisors** | security depois das duas: sem ERROR novo (os mesmos 2 views definer + 3 funções pré-existentes; 123 INFO) |
| **ROLLBACK** | `DROP INDEX IF EXISTS`; a coluna fica (expand-first) |
| **Aplicadas em produção** | sim · 14/09/2026 · `spec_extra001_2_check_fantasma_lid` e `spec_extra001_2_contraparte_unica` (MCP) |
| **Efeito de implantação declarado** | até o Implantar, conversas novas criadas pelo código antigo nascem sem `contraparte` (fora do índice, sem quebrar nada); depois do Implantar os dois resolvedores preenchem |

## 7. Painel: juiz fresco + lente do dado · conserto · suíte

### 7.1 Juiz fresco (Opus 5, sobre `c77f81c` · 📊 ≈199k tokens · 11 min) — **nota 62/100**

Critério: 100 = a §23 cumprida e nada cruza tenant nem duplica. As 3 perguntas fixas: (1) **dado vazio** — buffer vazio esperava 18 s antes de abrir turno sobre nada; tipo de mídia não classificado (vídeo, sticker) virava texto vazio e `branch=none` sem linha; escopo vazio cala sem feed (J10); (2) **duas corretoras** — nenhum cruzamento achado: buffer e trava carregam o escopo da integração, índice único é por `company_id`, plantão/colisão/memo filtram `company_id` duas vezes; (3) **a mesma mensagem 2×** — retry morre no `SET NX`; 2 workers → 1 resposta (`abrir_turno` antes do `get_and_clear`; 0 caminhos de disparo fora do buffer); mas as regenerações encadeiam (J8).

| # | grav. | o fato (prova) | destino |
|---|---|---|---|
| J1 | 🔴 BLOCKER | `janela_de_espera` devolvia **18 s para tudo sem pontuação** — 📊 70% dos itens do corpus versionado ("oi", "SOCORRO", "bateu meu carro" → 18 s); a D-E0012-10 mediu fragmentação, não latência | conserto (D-E0012-16) |
| J2 | 🔴 BLOCKER | turno vencido faz `return` seco com o buffer já consumido: a rajada some sem resposta; `renovar_turno` **sem chamador** no produto | conserto |
| J3 | ALTO | `classe_do_tamanho` casa "culpa" em "desculpa" e marca `avisar` a frase de acolhimento da própria docstring | conserto |
| J4 | ALTO | backfill da M2 recusa por comprimento, `contraparte_de` por sufixo (📊 medido em produção: **0** linhas divergentes); `get_or_create_conversation` termina em `raise` → um 23505 do índice novo derruba o turno | conserto (só a metade de código; sem M3) |
| J5 | MÉDIO | `apresentado_em` gravado na MONTAGEM do prompt: turno descartado → nunca se apresenta | conserto |
| J6 | MÉDIO | `turno_perdido` chega ao feed como token cru e divide a chave do memo com o takeover | conserto |
| J7 | MÉDIO | a linha combinada do pipeline (id da ÚLTIMA mensagem) colide com a do espelho no índice `messages_espelho_sem_duplicata_uidx`; os N−1 ids ficam fora do índice | conserto |
| J8 | MÉDIO | dois fiscais podem encadear 2 regenerações (3 chamadas de LLM) e o `AIMessage` novo perde `response_metadata`/`usage_metadata` | conserto |
| J9 | MÉDIO | produto lê `tests/fixtures/ancoras_de_pergunta_por_slot.json` | conserto (move para `app/resources/`) |
| J10 | BAIXO | rota sem integração: fail-closed certo, silêncio sem feed (não há `company_id`) | P-E0012-J10 |

Não verificado pelo juiz: banco (só leitura sem MCP), canário, se o DF roda hoje (📊 os 3 agentes ativos são `core`; o `display_name` do blueprint "AutoBrokers da {corretora}" duplicaria "da Resulta" na apresentação → conserto), a suíte inteira.

### 7.2 Lente do dado (Opus 5 · 📊 ≈146k tokens · 10 min) — **fidelidade dos números 88/100**

| # | afirmado | reconstruído | veredito |
|---|---|---|---|
| 1a | rajadas 85,5% do inbound | 20.871 · 85,5% (deriva de 1 dia) | SUSTENTA |
| 1b | faixa 0–3 s **59,7%** | com `<=3` 59,6%; com o operador do MOTOR (`gap<3`) **55,8%**; teto `>=25` 1.811, não 1.495 | 🔴 NÃO SUSTENTA (corrigido no §1.2 e no docstring do motor) |
| 1c | 6.213 rajadas ≥3: 17/44/39% · 67 s | 6.221 · 17/44/39 · 67 s | SUSTENTA |
| 1d | mediana 92 · p90 432 → 450 chars | 92 · 431 por BLOCO (o fiscal mede o turno inteiro antes dos balões — unidade certa) | SUSTENTA |
| 2 | 235 · 22 · 60 · 203 × 273 | **idênticos** com o motor real; 1.059 itens, 892 de texto; gap >25 s em 62 rajadas | SUSTENTA (rótulo corrigido) |
| 3 | turno p50 5,4 · p90 18 · máx 53 → TTL 90 | 5,4 · 17,9 · 53,4 (`core`; `attendance` máx 35,5) — é tempo do MODELO, não da posse | PARCIAL (D-E0012-01 anotada) |
| 4 | 54 · 37 · 72/56/16 | 54 ✅ · hoje `required − ROTULOS` = 0 · 72/56/16 ✅ | SUSTENTA (tempo verbal corrigido) |
| 5 | corpus 20 · A 11 · B 9 · 6 mídia · 17 um turno · 0 PII | idem; scan próprio (11 dígitos, 8+, placa, `@`, capitalizada) = **0** | SUSTENTA |
| 6 | 0 colisões · `Amanda` inativa · sem `attendant` | 0 pelo `colisao_com_a_equipe` REAL (8 agentes × 10 membros); 3 ativos todos `core`; papéis `{admin_company, member}` | SUSTENTA |
| 7 | 175 fantasmas · 0 duplicatas · 0 id repetido na conversa | 175/0 · 0 · 0 (887 conversas, 635 com contraparte, 34.952 messages) | SUSTENTA |
| 8 | (não medido) | **49,2%** das rajadas terminam num item que pedia 18 s; espera média **12,7 s × 8,0 s** da fixa; gap depois de inacabada p50 **7 s** · p75 14 s | 🔴 achado — mesma raiz do J1 |

Não reconstruível: a posse real da trava (só o canário); agente × humano no outbound (`direction='out'` não distingue → "92 chars é o que a humana faz" é INFERÊNCIA forte, ≥98% humano); sub-3 s (granularidade de 1 s do `wa_timestamp`).

### 7.3 Conserto único (Builder Opus 5 · 📊 ≈230k tokens · 1h20 · commit `d24eaa6`) — 9 de 9 achados de produto consertados, cada um com guarda que fica vermelho

| # | arquivo | o que mudou | guarda / mutação |
|---|---|---|---|
| J1 | `message_buffer_service.janela_de_espera` (+ docstring 55,8% / 72,4%) | 18 s exige `termina_em_conectivo`; sem pontuação = **8 s**; dado curto 3 s. 📊 Corpus recontado pelo motor: itens que pediam 18 s **37 (60,7%) → 1 (1,6%)**; espera média do último item **11,0 s → 7,0 s**; rajadas em 1 turno 17 → 12 (`turnos_esperados` regravado no jsonl; INDICE com o preço declarado) | G2b (9 frases pelo motor + contagem do corpus) · M-AB10 |
| J2 | `webhook._renovar_o_turno` (antes de gerar e antes de enviar) · `message_buffer_service.devolver_itens_ao_buffer` | `renovar_turno` ganhou chamador (2×/turno); posse perdida **devolve os itens ao buffer** (marca `reentregue`) em vez de `return` seco; `turno_perdido` só log | G5c · M-AB11 (não devolve) · M-AB12 (não renova) |
| J3 | `o_fim_do_atendimento.pergunta_delicada` · `classe_do_tamanho` | palavra inteira (`\b`, sem acento) **e na mesma frase interrogativa** | GD8j · M-D8i |
| J4 | `webhook._conversa_da_contraparte` + 23505 no insert · `espelho_chat` · docstring de `contraparte_de` | 23505 → relê pela chave do índice nos DOIS resolvedores; a divergência SQL × Python declarada (📊 0 divergentes; sem M3) | GE2f · M-E2b |
| J5 | `bloco_de_quem_fala` + `confirmar_apresentacao_enviada` · `attendance_ficha.identidade_vazia` · webhook passo 9 | a montagem só anota `apresentacao_pendente_*`; `apresentado_em` só depois de `send_message` True **e** se o texto enviado se apresenta (D-E0012-21: 92 × marcar em `agent_node` 70) | GD8g · M-D8f |
| J6 | `MOTIVO_TURNO_PERDIDO`, `_TOKENS_INTERNOS`, `frase_do_silencio` | `turno_perdido` fora do feed; classe própria com frase humana se entrar por outro caminho; entrada morta `sem corretora` removida | GE3g · M-E3z |
| J7 | `payload_do_pipeline` / `gravar_mensagem_do_pipeline` · `espelho_chat` | 📊 o espelho GRAVA inbound (`deve_espelhar` não filtra direção; 2 chamadores) na MESMA conversa → payload grava `wa_message_ids` (todos) e `wa_message_id` = primeiro; espelho **e** pipeline consultam `payload->wa_message_ids` antes de gravar | GE1f · M-E1d · M-E1e |
| J8 | `nodes.py` (`ja_regenerou`, `mesma_mensagem_com_texto`) | UMA regeneração por turno entre os fiscais; `response_metadata`/`usage_metadata`/`id` preservados | GD8i · M-D8h |
| J9 | `git mv tests/fixtures/… → app/resources/ancoras_de_pergunta_por_slot.json` | produto e testes leem de `app/resources/` (`COPY . .`, sem `.dockerignore`) | asserções em G7 |
| juiz | `linha_da_apresentacao` + `_nome_ja_diz_a_corretora` | nome que já contém a corretora → "Aqui é a {nome}, assistente virtual." | GD8h · M-D8g |

📊 Saída real: os 10 guardas **82 · 23 · 30 · 27 · 35 · 54 · 11 · 25 · 74 · 33 = 394 verdes, 0 vermelhas**; mutações **56 vermelhas, 0 verdes**; controles `test_midia_e_concorrencia_do_webhook` rc=0 · `test_a_maquina_de_lavar_vai_ate_o_fim` 112 · espelho ×2 rc=0 · `test_o_atendimento_termina_e_o_produto_sabe` 52 · `test_a_ultima_palavra_humana_manda` 26 · `test_a_janela_esta_ligada_nos_portoes` 7 · `test_higiene_de_plataforma` rc=0. Conferido pelo orquestrador (saída real): 394 verdes; mutações amostradas 12 + 5 + 10 vermelhas; 85 passed no pytest dos 3 controles. ⚠️ **A linha de controle do G2 morreu com o J1** (sobre este corpus a adaptativa e uma fixa de 8 s dão os mesmos 20 turnos) e foi substituída pelo estado de ANTES do J1 (18 s, erra 5 rajadas) + controle por item (≥4 itens diferem) → P-E0012-J1. Pendências do conserto: P-E0012-J1, J2, J5, J7, J10, J11 (PENDENCIAS.md).

### 7.4 Suíte inteira (árvore parada, `pytest tests -q -rfE`, 📊 saída real)

```
24 failed, 1114 passed, 34 xfailed, 1 xpassed, 45 warnings, 48 errors in 1290.46s (0:21:30)
```

Triagem, uma a uma, isolada e contra a base `47bc8e3` (extraída por `git archive` + `.env`):

| falha | causa | destino |
|---|---|---|
| 48 ERROR `test_098_builder_b_unit` | interferência de ordem da suíte (P-088-MUT): **80 passed** isolado | artefato conhecido |
| 13 `test_todos_os_guardas_script_rodam[...]` + `a_arvore_ficou_limpa` | idem: 6 dos 12 scripts passam isolados; `ontologia`, `sem_corredor_de_vidro`, `spec016×3`, `spec073` rc=0 | artefato conhecido |
| `test_o_numero_de_teste_e_conversa_nova::test_excecao_fala_mesmo_assumida` | 🔴 **verdade vencida** pelo BLOCO E (a exceção NÃO fura o takeover — era o "robô por cima da atendente") | migrado sob §9.3: assumida → cala; PAR: a exceção continua pulando a janela · **2 passed** |
| `test_a_atendente_fala_e_o_robo_cala` [h] | verdade vencida: "o script SABE que o CHECK ainda recusa `fantasma_lid`" — M1 aplicada | migrado: o script sabe que o CHECK aceita (6 motivos) · rc=0 |
| `test_o_atendimento_soa_humano` [4] [8] · `test_spec017_identity` (2) | verdade vencida pelo DF: sem nome o bloco de identidade EXISTE ("assistente virtual da corretora") e as 5 formas de handoff viraram 4 sem nome inventado | migrados: a lição (não inventar nome) fica · rc=0 ×2 |
| `test_o_protocolo_tem_policia` [7] | o card do relatório tinha "preenche no fim" | passa com este fechamento (conferido abaixo) |
| `test_a_atendente_aperta_o_botao_e_so_o_botao` · `a_central_diz_a_verdade` · `a_janela_esta_ligada_nos_portoes` · `a_resposta_chega_inteira` · `o_corpus_nao_vaza_pii` · `o_sinistro_deixa_rastro` · `toda_linha_tem_origem` · `todo_silencio_tem_motivo` | passam isolados (9 · 1 · 7 · 1 · 20 · 1 · 1 · 1) | artefato de suíte |
| `test_o_caso_se_explica_sozinho` [M1p] · `test_nenhuma_mutacao_foi_commitada` [2] (`route.ts` que não existe no commit) · `test_observador_silencio` ("decidir e gravar são blocos separados") · `test_spec031_finalize_v2` (`app.atendimento` não existe) | **falham igual na base `47bc8e3`** | pré-existentes, fora desta SPEC |

**0 falhas da SPEC** depois da triagem. Frontend: `npm run test:rotas-montam` → 301 rotas ordenadas; `tsc --noEmit` 0 erros.

## 8. Canário (depois do Implantar)

**Estado: NÃO TESTADO** — depende do Implantar de `smith-api` e `smith-web` (🧑). Roteiro pronto: `docs/canon/ROTEIRO-CANARIO-EXTRA-001.2.md` (8 casos da §16: rajada 5+foto → 1 turno; dado curto ~3 s; frase inacabada 15 s → 1 turno; mensagem durante o turno; presença só no caso 5 com `PRESENCA_DIGITANDO_LIGADA=true`; reencontro sem reapresentação; troca de nome + recusa; espelho com TESTE-B). Os casos 5 (calada → nenhuma presença) e 8 são as linhas de controle. Validação com as atendentes: `ROTEIRO-VALIDACAO-EXTRA-001.2-ATENDENTES.md` (8 perguntas). Nada foi ligado: `companies.agent_enabled` continua false em 5/5; `PRESENCA_DIGITANDO_LIGADA` nasce desligada.

### 8.1 aprovado no canário técnico — (vazio até o Implantar)
### 8.2 validado pela atendente — (vazio)

## 9. O que ficou fora e por quê

| item | por quê | onde mora |
|---|---|---|
| o nome do agente da Resulta | caixa do Founder (D-PILOTO-12); a SPEC entregou o mecanismo | P-E0012-D3 🧑 |
| papel `attendant` × `member` | decisão 🧑 (P-PILOTO-16); a regra (2) do plantão usa `member` | D-E0012-02 |
| plantão (regra 1 de `atendente_de_plantao`) | parâmetro pronto e testado; a 001.3 liga | BLOCO DF |
| filtrar a MEMÓRIA por assunto | apagaria fatos de apólice; o prompt desaconselha | P-E0012-D1 |
| migration M3 para o dialeto do backfill | 📊 0 linhas divergentes | D-E0012-18 |
| `provider_message_id` atravessar a fachada | fora da superfície; a resposta da IA fica fora do dedupe durável | P-E0012-02 |
| unificar `ROTULOS` × `_COMO_PERGUNTAR` | segundo vocabulário achado no BLOCO C; G6 fica vermelho se divergirem | P-E0012-C2 |
| âncora de bloco para os 12 slots de endereço | 16 slots sem âncora | P-E0012-C3 |
| modelos de dossiê | são da 001.3; aqui só a assinatura | §10.5 |

## 10. Decisões tomadas com nota

| id | decisão | opções e notas | por quê |
|---|---|---|---|
| **D-E0012-01** | `TURNO_TTL_SEGUNDOS` = 90, 3 renovações | 90 **85** · 60 **55** (máx medido 53 s + envio) · 180 **40** (trava órfã longa) | premissa 5 · ⚠️ lente ②: o 53 s é `response_time_ms` (tempo do MODELO, papel `core`; `attendance` máx 35,5 s) — a posse real inclui visão/transcrição e balões e só o canário a mede; o juiz J2 achou `renovar_turno` sem chamador → conserto |
| **D-E0012-02** | `atendente_de_plantao` regra (2) usa `company_members.role='member'` ativo e não-owner (não existe `attendant`) | member **80** · criar papel `attendant` agora **25** (P-PILOTO-16 é decisão 🧑) | D3 |
| **D-E0012-03** | P-PILOTO-15 pela opção (b′): a pausa protege quando o takeover (`claimed_at`) é DEPOIS do encerramento (`resolvido_em`); nenhum leitor de `resolvido_em` muda | (b′) **88** · (a) limpar `resolvido_em` **35** (📊 12 leitores; apagaria o fato de que terminou) · (b) ingênua **40** (volta o "calado para sempre" de 05/09) | Builder E |
| **D-E0012-04** | `CAMPOS_DE_CONTROLE = {dados_confirmados}` — o único campo da tool que não é fala do cliente | **90** | Builder C |
| **D-E0012-05** | `confirmados[slot]` vira `{valor, origem, em}` com leitura tolerante ao valor cru; origem `sistema_de_gestao` só para placa/veículo com contexto InfoCap; CPF fica `cliente` | **92** · valor cru + mapa paralelo de origem **40** | Builder C |
| **D-E0012-06** | o índice único da M2 só entra com D0 = 0 duplicatas abertas (havia 0); duplicatas viram lista no relatório, nunca fechamento em lote | **92** · fechar a mais antiga **20** (D-PILOTO-02) | Builder E |
| **D-E0012-08** | escopo vazio na trava de turno → RECUSA (fail-closed) em vez de chave global `whatsapp_turno::phone` | recusar **92** · chave global **30** (duas corretoras com o mesmo telefone disputariam um turno) | Builder AB |
| **D-E0012-09** | visão e transcrição rodam dentro do TURNO, não no recebimento | no turno **90** (a legenda que chega 2 s depois entra no mesmo contexto) · no recebimento **55** (mais cedo, mas responde a meia rajada) | Builder AB |
| **D-E0012-10** | janela 3 · 8 · 18 s com teto 25 confirmada (📊 adaptativa fragmenta 203 × fixa 273 sobre 400 rajadas); o teto só desce | **94** · fixa 8 s **60** · fixa 25 s **45** (lenta em toda conversa curta) | Builder AB · 🔴 **REVISTA no conserto (D-E0012-16)**: a nota media só a fragmentação; a lente mediu o CUSTO (49,2% das rajadas terminam num item que pedia 18 s; espera média 12,7 s × 8,0 s da fixa; gap depois de inacabada p50 7 s · p75 14 s) e o juiz mediu que 70% dos itens do corpus caíam em 18 s |
| **D-E0012-11** | re-planejamento ANTES de gravar e gerar (teto 2) | **88** · re-gerar depois da geração **50** (custo dobrado) · ignorar o que chegou **20** (volta o "uma por uma") | Builder AB |
| **D-E0012-12** | sem `delay` no `/send/text`; a presença é chamada explícita e só depois do portão de silêncio | **85** · `delay` no send **60** (o GO simularia "digitando" mesmo quando o portão manda calar) | Builder AB |
| **D-E0012-13** | o teto de tamanho da classe conversa é DUPLO: 3 frases E 450 chars (📊 p90 = 432 no acervo; mediana 92) | duplo **92** · só frases **40** (o defeito de 10/09 tinha 760 chars em 3 frases e passaria) | Builder DF |
| **D-E0012-14** | a recusa de nome colidente mora na rota do Next que grava `attendant_name`, não no FastAPI (que não grava o campo) | Next **85** · FastAPI **30** (validaria um caminho que ninguém usa) — fica **P-E0012-D4** | Builder DF |
| **D-E0012-15** | o bloco de MEMÓRIA não é filtrado por assunto; o prompt desaconselha o nome vindo dela | desaconselhar + P-E0012-D1 **70** · suprimir memória no atendimento **45** (apagaria fatos de apólice) · marcar PII no `MemoryService` **80 mas fora do escopo** | Builder DF |
| **D-E0012-16** | REVISÃO da D-E0012-10 depois do painel: 18 s SÓ quando a mensagem termina em conectivo; sem pontuação = 8 s; dado curto = 3 s | conectivo-só **90** · manter 18 para tudo sem ponto **20** (📊 70% dos itens; +4,7 s por rajada) · 15 s para tudo **50** | J1 + lente ⑧ |
| **D-E0012-17** | posse perdida ANTES do envio devolve os itens ao buffer (re-`add`, marca `reentregue`); `renovar_turno` antes da geração, de cada regeneração e do envio | **92** · `return` seco **0** (rajada perdida) · TTL 300 sem renovar **35** (trava órfã de 5 min) | J2 |
| **D-E0012-18** | J4: sem migration M3 — 📊 0 linhas divergentes em produção; a divergência de dialeto vira docstring de `contraparte_de`; o 23505 é relido nos DOIS resolvedores | **90** · M3 no-op **20** | J4 |
| **D-E0012-19** | uma regeneração por turno entre os fiscais (o 2º só registra); metadados preservados ao substituir a resposta | **90** · encadear **30** (3 LLM num TTL de 90 s) | J8 |
| **D-E0012-20** | `ancoras_de_pergunta_por_slot.json` mora em `app/resources/`; os testes leem de lá | **92** | J9 |
| **D-E0012-07** | o feed do silêncio é escrito DENTRO de `a_ia_deve_calar`, memo por CLASSE (não pela frase, que carrega nome) | **85** | Builder E |

## 11. Riscos remanescentes

1. **A posse real da trava não foi medida** (só `response_time_ms`); com mídia no turno + 1 regeneração o turno pode passar de 90 s e depender das renovações (3). O canário mede; P-E0012-J11.
2. **Latência sentida:** mesmo com o J1, dado curto 3 s e frase 8 s são espera ANTES de gerar; o piloto 001.7 é quem decide se 8 s incomoda.
3. **A corrida espelho × pipeline** não duplica mais, mas pode perder o texto combinado (P-E0012-J7).
4. **A memória** pode trazer nome de assunto antigo (P-E0012-D1).
5. **Todo inbound passa pelo buffer agora** — o corredor da seguradora herda a janela (a 001.4 decide se o humano da seguradora merece janela própria).
6. **`display_name` do blueprint** ("AutoBrokers da {corretora}"): a apresentação não duplica mais, mas o nome de fato é caixa 🧑.
7. **Env novas** têm default; se o EasyPanel definir `PRESENCA_DIGITANDO_LIGADA=true` antes do canário, a presença sai sem ter sido vista.

## 12. Rollback

- **Código:** `git revert` dos commits da SPEC na `main` (de `0fdda09` a este fechamento) — nenhum passo destrutivo no código; as 7 env novas podem ficar (têm default) ou ser removidas.
- **M1 (`20260914_07`):** o ROLLBACK escrito RECUSA reverter enquanto houver linhas com `fantasma_lid` (📊 175) — reverter deixaria 175 `closed` sem motivo válido. Se preciso: `UPDATE conversations SET resolucao_motivo='expirou' WHERE resolucao_motivo='fantasma_lid'` (perde a distinção) e depois o ROLLBACK do arquivo.
- **M2 (`20260914_08`):** `DROP INDEX IF EXISTS uq_conversations_contraparte_aberta;` — a coluna `contraparte` fica (expand-first, nada a lê de forma obrigatória).
- **Dados:** as 175 fantasmas fechadas e as 2 pausas copiadas ficam (nenhuma mensagem apagada); reabrir seria `status='open'` por `resolucao_motivo='fantasma_lid'`, não recomendado.
- **Redis:** `DEL` das chaves `whatsapp_turno:*` órfãs se um rollback de código deixar trava aberta (TTL 90 s as apaga sozinho).

## 13. Entrega (`git push`, saída colada)

Preflight (📊 saída real, 15/09/2026): `git fetch` · `HEAD..origin/main` = **0** · `origin/main..HEAD` = **14** · `merge-base --is-ancestor` ✅.

```
$ git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   47bc8e3..fc75193  HEAD -> main
$ git rev-list --count origin/main..HEAD
0
```

**`main` = `fc75193`** (14 commits da SPEC: `0fdda09` BLOCO 0 · `2c18547` E · `610d76d` C · `2111cca` · `56d8bb3` AB · `c77f81c` DF · `d24eaa6` conserto · docs). Os commits de fechamento que vêm depois desta seção (ESTADO/INDICE, página do dossiê) sobem num segundo `git push` com a mesma forma; o hash final fica em `ESTADO-DAS-SPECS.md`.

**Deploy (🧑, EasyPanel → Implantar):** `smith-api` (obrigatório) e `smith-web` (a frase de recusa do nome no card Agente). `portal-worker` não muda. Migrations `20260914_07` e `_08` já aplicadas. **Env por nome** (todas opcionais, com default): `TURNO_TTL_SEGUNDOS` · `TURNO_RENOVACOES_MAX` · `JANELA_DADO_CURTO_SEGUNDOS` · `JANELA_FRASE_COMPLETA_SEGUNDOS` · `JANELA_FRASE_INACABADA_SEGUNDOS` · `PRESENCA_DIGITANDO_LIGADA` (deixar ausente/false até o caso 5 do canário) · `REPLANEJAMENTOS_MAX`. Nada foi ligado. Rollback: §12.
