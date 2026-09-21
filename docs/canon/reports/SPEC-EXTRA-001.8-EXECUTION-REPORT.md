# SPEC-EXTRA-001.8 · Uma corretora não trava a outra — relatório de execução

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — reconferido no BLOCO 0 sobre `bfa0a40`

```
OUTCOME ..............  4+ atendimentos simultâneos POR CORRETORA; uma corretora lenta, travada ou em rajada
                        não muda a latência da outra; zero mensagem perdida, e o número da perda aparece na
                        corretora certa
RISCO ................  8 = alcance 3 (o segurado) + reversibilidade 3 (a mensagem sai do prédio) + frequência 2
SUPERFÍCIE ...........  2
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" + "o filtro company_id" → CRÍTICO
NÍVEL ................  CRÍTICO · builders Opus 5 xhigh · juiz Fable ‖ red team Fable, cegos · confirmação
O FIO ................  webhook.py:_buffer_or_dispatch_text → message_buffer_service.add_message (Redis) →
                        buffer_processor.check_buffers (1 s) → prontas() MGET → ordenar_em_rodizio →
                        _uma(): cota do escopo → teto global → abrir_turno (001.2) → get_and_clear_buffer →
                        webhook.process_whatsapp_message_background → llm_factory (teto por chamada) +
                        relogio_do_modelo (disjuntor por provedor) → whatsapp_service.send_message →
                        messages.payload.turn → central_de_agentes.atendimento_por_corretora
                        · testes do fio: test_o_fio_inteiro_do_isolamento.py + test_a_costura_do_isolamento.py
PARALELISMO REAL .....  2 escritores com arquivos disjuntos ({llm_factory + relogio_do_modelo} ∥
                        {buffer_processor + message_buffer_service}); a costura e a Central em série
UNIDADES .............  7 (A medição · B cota+rodízio · C teto/retry/disjuntor · D contrapressão · E processos
                        e líder · F observabilidade por corretora · G prova) — 6 fatias de builder
COESÃO ...............  `buffer_processor.py` é ARQUIVO-HUB (A, B, D, F escrevem nele): um dono por vez
TIME .................  6 builders Opus · 1 leitor · juiz Fable ‖ red team Fable · confirmação · docs
REFERÊNCIA ...........  interna `app/workers/smith_worker.py:252-278` (a cota por tenant que já roda em
                        produção) e `tests/test_midia_e_concorrencia_do_webhook.py:519` (controle herdado) ·
                        externas: SPEC §17 E1 Bulkhead · E2 k8s APF · E3 Redis SET NX
GATES ................  G1–G10 · S1 · S3 · G11 · casos 6–8 da costura · cenário (k) · [6] — todos verdes;
                        G (canário) PARCIAL NOMEADO, na caixa do Founder
O ELO ................  "A atrasa B porque compartilham recurso sem partição": 4 recursos medidos um a um, e
                        um 5º achado no BLOCO 0 (o semáforo nascia por varredura, não por processo)
FAIXA DE RELÓGIO .....  declarada 💭 8–12 h · real: §11 (telemetria)
X do G3 .............   X = max(piso 0,120 s; p95 sozinha × 0,25)
                        comando: `python tests/test_uma_corretora_nao_trava_a_outra.py --so G3`
```

**SPEC:** `specs/SPEC-EXTRA-001.8-uma-corretora-nao-trava-a-outra.md` · **Branch:**
`feat/spec-extra-001.8-isolamento-por-corretora` · **Preflight 📊 21/09:** `HEAD..origin/main` = 0 ·
`origin/main..HEAD` = 0 · **commit inicial** `bfa0a40` · **commit final** `477a0bc` (+ o conserto do resíduo,
`3a6d22c`) · 📊 `git diff --stat bfa0a40 477a0bc` → **43 arquivos · 11.207 inserções · 196 deleções ·
8 commits**. **Estado final: CONCLUÍDA COM RESSALVA** — a ressalva é o canário (§6).

## 1. BLOCO 0 — o que foi remedido antes de codar (📊 21/09/2026)

⚠️ A proposta mandava rodar "as 16 premissas do RESEARCH-PACK §2". **FATO: o RESEARCH-PACK não existe no
repositório.** O BLOCO 0 abaixo o substituiu.

| # | 📊 medido, e a consequência | comando |
|---|---|---|
| B0.1 | semáforo global de 6 com `should_process` **dentro** dele — é o elo ① | leitura `buffer_processor.py:77-81` |
| B0.2 | **0** linhas de `wait_for`/`timeout` no processador | `grep -n "wait_for\|timeout" app/tasks/buffer_processor.py` |
| B0.3 | **0** linhas de `timeout`/`max_retries` na fábrica | `grep -n "timeout\|max_retries" app/factories/llm_factory.py` |
| B0.4 | ⚠️ **326** `asyncio.to_thread` (a proposta dizia 306) · **0** `set_default_executor` | `grep -rn "asyncio.to_thread" app/ \| wc -l` |
| B0.5 | `BUFFER_TTL_SECONDS = 60`, dois pontos de escrita | `core/config.py:75` · `message_buffer_service.py:463,622` |
| B0.6 | ⚠️ **25** jobs registrados (a proposta dizia 24) | `grep -c "scheduler.add_job" app/tasks/buffer_processor.py` |
| B0.7 | a trava de turno da 001.2 **já está na árvore** → o plano B da proposta §3.3 caiu | leitura `abrir_turno`/`fechar_turno` |
| 🔴 B0.8 | **ACHADO DO GERENTE:** `check_buffers` roda a cada 1 s com `max_instances=10` e **cada varredura criava o SEU `asyncio.Semaphore(6)`** → o "teto de 6" real chegava a **60**, e uma cota local viraria **40**. Por isso o estado de admissão passou a viver **no MÓDULO** | leitura + medição |
| B0.9 | produção, n=**41** turnos do **chat do painel**, 09/09–17/09: mediana **39.133 ms** · p95 **107.047 ms** · máx **135.585 ms**. É **TURNO** (várias chamadas), não chamada única ⇒ a regra "p95×3" da proposta **não se aplica** ao teto por chamada. Amostra pequena, declarada | `SELECT count, percentile_cont(.5/.95), max` sobre `messages.payload->'turn'->>'total_ms'` |
| ⛔ B0.10 | **NÃO MEDIDO:** `cpu_count` do contêiner `smith-api` implantado — sem acesso ao contêiner. Vai para a caixa do Founder (P-E0018-02); o poço já é ≥ 32 por default | — |

## 2. O que foi entregue, por fatia

| fatia | entrega | arquivos principais | commit |
|---|---|---|---|
| F2 | **relógio do modelo**: teto 90 s + `max_retries` 2 nos 4 construtores, disjuntor por provedor, 4 clientes httpx com teto | `relogio_do_modelo.py` (novo) · `llm_factory.py` · `mcp_servers/*` · `mcp_oauth_service.py` | `4c207c6` |
| F1 | **cota 4 por corretora, rodízio, espera que não perde mensagem**; estado de admissão no MÓDULO | `buffer_processor.py` · `message_buffer_service.py` | `37dcfc0` |
| F3a | **cerca de corretora DENTRO do serviço MCP** (P-098), com dois tenants | `api/mcp.py` · `mcp_oauth_service.py` | `d339aa5` |
| F3b | **nome de pessoa real sai do dado global** de corredor (P-E00151-09) | `corridor_playbooks.py` + 14 arquivos de comentário | `658debf` |
| F4 | **só um agendador manda** (lock de líder com token, 25 jobs classificados), poço de threads explícito, o processador pergunta ao disjuntor **antes** de consumir | `lider_do_agendador.py` (novo) · `main.py` · `buffer_processor.py` | `3707bc8` |
| F5 | **`payload.turn` no atendimento**, Central por corretora, aviso ao dono pronto e **desligado** | `webhook.py` · `central_de_agentes.py` · `aviso_de_fila_longa.py` (novo) · `admin/central-agentes/page.tsx` | `47d4773` |
| F6 | **a costura**: o processador conta a espera ao webhook, o resumo da varredura passa a ser **por corretora**, o aviso fica ligado ao processador (flag desligada) | `buffer_processor.py` · `webhook.py` | `23560d1` |
| — | **conserto único dos dois laudos** (§4) | 9 arquivos | `477a0bc` |

**Migrations: nenhuma.** Zero SQL, zero DDL, zero backfill — o turno cabe em `messages.payload` (jsonb), os
contadores/lock/disjuntor em Redis, e a Central no JSON do endpoint que já existe.

📊 **Gate do Next** (fatia F5): `tsc` limpo · `npm run test:rotas-montam` → **303 rotas** · build 0 ·
`next start`: `/api/admin/spec034/agents-status` → **401** (sem chave, o esperado) e `/login` → **200**. O juiz
reconferiu `test:rotas-montam` (verde).

## 3. Testes — saída real (📊 reconferida pelo gerente em 21/09, depois do conserto; `python tests/<arq>.py`, rc=0 em todos)

```
test_o_fio_inteiro_do_isolamento.py ........ 50 ok      test_a_costura_do_isolamento.py ...... 47 ok
test_so_um_agendador_manda.py .............. 78 ok      test_o_modelo_tem_relogio.py ......... 66 verdes
test_uma_corretora_nao_trava_a_outra.py .... 62 verdes  test_o_atendimento_tem_relogio.py .... TUDO VERDE
test_a_central_ve_por_corretora.py ......... verde      test_o_mcp_tem_cerca_de_corretora.py . 40, 6 mutações
test_nenhum_nome_de_gente_em_dado_global.py  verde      test_a_atendente_fala_e_o_robo_cala.py TUDO VERDE
LINHAS DE CONTROLE HERDADAS (test_midia_e_concorrencia_do_webhook.py, test_uma_rajada_um_turno.py):
`git diff --stat` VAZIO nos dois — não foram tocadas, e estão verdes
```

📊 **Placar de mutações vermelhas** (relato dos builders, depois do conserto): fio 6→7 · cota 8→10 · costura
4→7 · agendador 7→8 · modelo 7 · MCP 6 · nome 2 · relógio/Central/aviso 6.

📊 **O X do G3, medido** (§5.4 da SPEC): antes do conserto — p95 da sadia sozinha **0,0012 s** · com a doente
**0,0215 s** · CONTROLE com a cota desligada **2,4554 s**. Depois do conserto, 10 rodadas — p95 com a doente
**0,0211–0,0294 s** · CONTROLE **4,84–4,95 s** · **10/10 verde**.

⚠️ **Honestidade do método:** três scripts de atacante não mostram o conserto porque **reimplementam** o trecho
consertado (`atk3c`, `medir.py` M3, `medir2` M5b). Nesses casos a prova é o guarda novo, com motor real e linha
de controle — não o script do laudo.

## 4. 🔴 O julgamento — 1 rodada paralela (juiz Fable ‖ red team Fable, frescos, cegos um ao outro)

⚖️ **Juiz:** NÃO LIBERA · **nota 76/100** · confiança 80 · 5 blockers. 🗡️ **Red team:** QUEBREI · **nota 78/100**
· confiança declarada · 2 blockers + 9 pendências. **Autoria reconferida contra os laudos completos**, achado a
achado, antes de escrever esta tabela.

| # | achado (📊 reproduzido com o motor real) | juiz | red team | **EXCLUSIVO de** |
|---|---|---|---|---|
| A1 | 🔴 `expiradas`/`timeouts` são totais **globais** da varredura e são gravados no hash de **TODO** escopo presente (a perda de A aparece na tela de B, e multiplica); turno cortado vira "expirada" na varredura seguinte; mensagem **mesclada** ao turno em voo também | B3 | B1 (b, c) | — (os dois) |
| A2 | 🔴 corrida do `servidas.clear()` entre varreduras sobrepostas: conversa **RESPONDIDA** vira "expirada". 📊 `atk1b`: 3 de 3 respondidas, e a Central mostra 1 perda na corretora errada | — | B1 (a) | **red team** |
| A3 | 90 s × 3 tentativas = **270 s** > teto do turno 180 s: o corte vem antes do erro final, e o disjuntor **nunca abre** com provedor pendurado | B2 | B2 | — (os dois) |
| A4 | 🔴 o corte cancela com `CancelledError`, que **não é `Exception`** → o bloco do aviso honesto do webhook **não roda**: segurado em **silêncio definitivo** | — | B2 | **red team** |
| A5 | 🔴 `max_instances=10` + varredura que vive enquanto o turno vive → **teto real 10, não 24**: com 3+ corretoras carregadas a 4ª não é olhada e **ninguém renova o TTL** de quem espera. 📊 `medir_instancias.py 10` → a 4ª esperou 3,32 s; com 100 (controle) → 0,15 s | B1 | — | **juiz** |
| A6 | `total_ms` soma `fila_cota_ms` **duas vezes** (já está dentro de `buffer_espera_ms`) — infla o p95 justamente sob carga | B4 | P5 (pendência) | — (os dois; **só o juiz** classificou blocker) |
| A7 | `provedor_disponivel` (a sonda do meio-aberto) **sem chamador**: o meio-aberto libera **todas**. 📊 8 consumidas × 0 no controle | B5 | P3 (pendência) | — (os dois; **só o juiz** classificou blocker) |
| A8 | achado do **PRÓPRIO CONSERTO**: `_fechar_a_conta` reinscrevia em `aguardando`, no fim da varredura, chave que uma varredura sobreposta já respondera | — | — | **builder do conserto** |

**Pendências do juiz (9):** G3 pisca no Windows · dois guardas constroem cliente Supabase real · líder não
reconhece o próprio cadeado depois de um soluço do Redis · o aviso ao dono toma a janela antes do envio ·
`except BaseException` engole `CancelledError` · comentário vencido · 📊 sem a query ao lado ·
`espera_do_backoff` sem chamador · 4 GETs sequenciais por varredura.
**Pendências do red team (9):** P1 corte **durante** o envio (os balões restantes saem depois de a trava ser
solta, e o log diz "nada foi dito") · P2 `except BaseException` · P3 sonda sem chamador · P4 **LLM de VISÃO fora
da fábrica** · P5 `total_ms` · P6 varredura vazia foi de 1 para 9 idas ao Redis · P7 timeout do Redis na
renovação rebaixa o líder ~40 s · P8 teto global bloqueante acumula esperadores-fantasma · P9
`routine_scheduler_loop` fora do cadeado.

🛡️ **O que o red team NÃO quebrou, e é o que mais importa** (palavra dele): **nenhuma mensagem perdida nem
duplicada** no fio cota → teto → disjuntor → trava → `get_and_clear`; a **vaga de cota não vazou** em nenhum
caminho (timeout, exceção, cancelamento, adiamento); o teste do fio é honesto (3 mutações dele ficaram
vermelhas); nenhum caminho de atendimento fora do buffer; 9 rotas MCP, o state OAuth e o UPDATE do relógio
cercados por corretora; mensagem nova durante o adiamento não se perde.

🔴 **A maior lacuna (juiz):** nenhum guarda rodava **o agendador REAL** com turnos longos — por isso A5
atravessou 9 guardas verdes. O conserto criou esse guarda (cenário **k**, APScheduler real).

## 5. O conserto único (`477a0bc`) e a confirmação

O conserto fechou **A1–A8**, subiu o piso do G3 para 0,120 s (10/10 verde), derrubou a varredura vazia de 8 para
**0** consultas ao disjuntor, corrigiu comentários e dublou dois guardas que construíam cliente Supabase real.
⚠️ Um teste existente foi **reescrito por verdade vencida** (CLAUDE.md §9.3): `test_o_atendimento_tem_relogio.py`
[3b] afirmava a soma que **era** o defeito A6; a asserção nova é mais apertada (exige `total_ms ≥ 11000` **e**
`total − 11000 < 1008`). Três âncoras de mutação acompanharam o texto novo (M-C-1, M-E-6, M-FIO-3).

🏁 **Confirmação** (juiz novo, só o diff `23560d1..477a0bc`): **LIMPO COM PENDÊNCIAS · nota 86/100** · confiança
80. **O conserto NÃO criou defeito.** Os sete riscos examinados saíram sem defeito: o `raise` do `CancelledError`
acontece em todo caminho; o ramo de áudio/foto não dispara o aviso (sem duplicata); num shutdown o segurado passa
a receber o aviso honesto onde antes havia silêncio; uma corretora sozinha **não** consegue abrir o disjuntor por
cortes (cota 4 < 5 falhas em 60 s); `max_instances=40` não deixa trabalho periódico parado e `coalesce` +
`misfire_grace_time=1` impedem avalanche; a sonda gasta vence em 30 s; e antes de enviar, `ainda_sou_o_dono`
descarta o turno sem posse.

🔴 **RESÍDUO B1 (não é regressão — pré-existente, medido nas duas versões):** com o teto global cheio e duas
varreduras sobrepostas, S1 consome a chave e a marca consumida, S2 recebe `abrir_turno → None` e **reinscreve a
chave em `aguardando` depois do consumo** → a varredura seguinte conta 1 "expirada" no hash do dono para uma
conversa **respondida**. 📊 `m1_corrida_sobreposta.py` → controle **0** · corrida **1**; o mesmo script contra o
código **de antes** do conserto também dá 1. **DECISÃO DO GERENTE: consertar** (nota 90 × registrar como
pendência 55) — é o número que o Founder olha todo dia, e o conserto de 7 linhas foi medido em cópia (→ 0). Cabe
na regra ≤ 30 min / ≤ 2 arquivos / sem decisão; **não** é 3ª rodada de julgamento. Aplicado **depois da bateria**:
**conserto do resíduo: `3a6d22c`**.

📊 **Blockers EXCLUSIVOS por mecanismo:** juiz **1** (A5) · red team **2** (A2, A4) · conserto **1** (A8) ·
confirmação **1** (o resíduo). Três achados foram dos **dois** laudos (A1, A3) e dois foram de ambos com
classificação diferente (A6, A7 — blocker no juiz, pendência no red team).

## 6. 🔴 CANÁRIO — PARCIAL NOMEADO (não rodou)

**FATO:** o canário **não rodou**. Ele exige TESTE-A e TESTE-B pareados em **duas corretoras de teste
distintas**, e Implantar — ação física do Founder (CLAUDE.md §10-5). **Ausência de canário não vira aprovação.**
Os seis casos que faltam: **(1)** linha de base sem doente · **(2)** 🔴 o gate: a corretora 2 travada de
propósito + rajada sintética, com TESTE-A na corretora 1 ao mesmo tempo (caso 2 ≤ caso 1 + X) · **(3)** TESTE-B
na doente é atendido, lento mas atendido · **(4)** rajada de 50 mensagens com `expiradas` = 0 · **(5)** disjuntor
aberto na corretora 2 sem a corretora 1 sentir, com **um** aviso ao dono · **(6)** allowlist esvaziada e o
número do caso 1 de volta. **INFERÊNCIA:** o isolamento está provado por teste sintético sobre o motor real, com
linha de controle — não por produção. **RECOMENDAÇÃO:** rodar os 6 casos logo após Implantar (P-E0018-01).

## 7. As decisões do executor, com nota (viram `D-E0018-01…16` em `FOUNDER-DECISIONS.md`)

Estado de admissão no **módulo** 92 (local à chamada: furo medido) · cota **não-bloqueante** com `adiar` 92 ×
semáforo por corretora 48 · teto por chamada **90 s** 85 × "p95×3" 40 · teto por turno 180 s na construção
(82 × 120 s da proposta 55) → **300 s** no conserto 85 × baixar a chamada para 60 s 60 · timeout de turno **não**
devolve a rajada 88 × devolver 45 · `sem-integracao` adiada sem renovar vida 90 · dois defaults de paralelismo 85
× editar o guarda herdado 70 · **401 nunca abre o disjuntor** (a chave é global) · disjuntor alimentado por
callback + pergunta antes de consumir 92 · **não** mexer no `graph.py` 85 × 62 · cerca MCP dentro do serviço 92 ×
coluna nova 41 × só RLS 35, e **404 em vez de 403** 84 × 78 · varredura do buffer fora do lock 92 × 38 ·
`pause_job`/`resume_job` 93 × shutdown+start 22 · poço `max(32, cpu+4)` 91 · costura do disjuntor opção (ii) 90 ·
UPDATE do turno por id+`conversation_id` **depois** do envio 92 · `stages`/`stage_ms` com o vocabulário do chat
88 · **`expiradas_acumuladas`** em vez de `expiradas_24h` 92 · `fila_cota_ms` desde o 1º adiamento 88 × "última
tentativa" 62 · `max_instances` = 24+16 = 40 82 × redesenhar a varredura 75 · **protocolo v13.1** (D-PROTO-13) 90.

## 8. 📋 Caixa do Founder

1. **Implantar** `smith-api` e depois `smith-web` (o portal-worker não muda). Nada no ar muda de comportamento
   visível: todas as variáveis novas têm default no código, e o aviso ao dono nasce **desligado**.
2. Conferir no **`/health`**: `scheduler` deve dizer `lider`, e `executor_threads` deve trazer um número.
3. **Medir os núcleos do contêiner** — no console do `smith-api`:
   `python -c "import os; print(os.cpu_count(), min(32,(os.cpu_count() or 1)+4))"` (P-E0018-02).
4. Olhar **"Mensagens perdidas"** por corretora na Central de Agentes — é a resposta diária a *"perdi alguma
   mensagem?"*, e agora ela aparece na corretora certa.
5. 🔴 **O canário**, com duas corretoras de teste e os 6 casos do §6 (P-E0018-01).
6. Decidir se cria o **serviço de jobs separado**: o código já sai pronto (`SCHEDULER_ENABLED`).
7. 🔴 **NÃO ligar `ISOLAMENTO_AVISO_AO_DONO`** antes de P-E0018-09 (a janela de 30 min é tomada **antes** do
   envio; um envio que falha queima a janela e o dono fica sem aviso).

## 9. O que ficou fora, riscos e pendências

**Fora, com gatilho escrito na SPEC §18:** executor de threads por caminho · rate limit por corretora na entrada
· `uvicorn --workers` · serviço de jobs separado · borrowing entre corretoras · Prometheus/OTel · pool de banco
por corretora · a presença "digitando…" no adiamento por cota (P-E0018-10).

**Riscos remanescentes** (em `PENDENCIAS.md`, `P-E0018-01…29`): 🔴 **P-E0018-03** — com o Redis fora, o webhook
devolve 500 e a mensagem do segurado **não é gravada em lugar nenhum**: é anterior a esta SPEC e está numa camada
que ela não tocou · 🔴 **P-E0018-04** — `get_async_redis_client` não memoriza a falha e cada chamada paga até 5 s
· 🔴 **P-E0018-13** — `get_agent_oauth_tokens` ainda age por `agent_id` puro (a última porta sem cerca do módulo)
· 🔴 **P-E0018-14** — `conduct_playbooks` é tabela **GLOBAL sem `company_id`**, escrita a partir de conversas de
UMA corretora (hoje 18 linhas, 0 nomes): **candidata ≥ 90 pela D-FILA-01** · P-E0018-05 (LLM de visão fora da
fábrica) · P-E0018-06/07 (escala da varredura e do teto global) · P-E0018-17 (o juiz de evals nunca deu veredito)
· P-E0018-22 (duas falhas de teste **pré-existentes**, provadas contra a base).

**Pendências antigas re-julgadas:** **P-098-MCP-ROTAS-SEM-COMPANY** FECHADA (`d339aa5`) · **P-E00151-09**
FECHADA para `backend/app` e scripts (`658debf`; resíduo em fixtures) · **P-PILOTO-01** fechada no código,
**CONTINUA** até o canário · **P-238 CONTINUA e foi AGRAVADA de propósito** (sem Redis os jobs que enviam são
fail-closed) · **P-248 PARCIAL** (o `/health` ganhou `scheduler` e `executor_threads`; falta `worker_ligado`) ·
P-096, P-207 e P-237 CONTINUAM, não tocadas.

## 10. ⚠️ Quebras de regra DECLARADAS

(a) o gerente leu a proposta **inteira** (62 KB, acima do teto de 40 KB) porque não existe FICHA desta SPEC;
(b) **12 agentes** (1 leitor, 6 builders, juiz, red team, conserto, confirmação, documentos) — dentro do teto de
24 da D-PROTO-11, e acima do "≤ 6" que o protocolo trazia antes do v13.1; (c) o builder do conserto passou de
250 turnos / 300 k numa fatia só (relatou **411 k** tokens); (d) **a bateria e a confirmação rodaram ao mesmo
tempo**, com o juiz da confirmação proibido de mutar a árvore; (e) **o contexto do gerente passou de 300 k**.

## 11. 🔴 Nenhum motor paralelo foi criado (CLAUDE.md §5)

**Zero fila nova, zero scheduler novo, zero tabela, zero migration, zero rota nova, zero tela nova.** A cota e o
rodízio vivem **dentro do processador que já existia**; o lock apenas decide se o agendador que já existia liga;
o disjuntor é uma peça nova **por provedor de LLM** e não duplica o disjuntor de portal da 001.6 (outro assunto,
outro processo); a Central ganhou um bloco no JSON do endpoint existente, e o frontend, uma seção na página que
já existe.

## 12. A bateria e a entrega

📊 **Bateria:** 1 rodada inteira, DEPOIS do conserto único (`477a0bc`), 21/09/2026, `cd backend && python -m pytest tests -q -p no:cacheprovider` → **40 failed · 1222 passed · 34 xfailed · 1 xpassed em 3.226 s**. Triagem NOMINAL: 6 nomes fora da base (`test_o_protocolo_tem_policia`, da base, passou). **2 eram regressão desta SPEC, no GUARDA e não no produto** (`test_higiene_de_plataforma`, que recorta `chave()` do fonte; `test_o_segurado_nao_fica_no_escuro`, que lia o aviso honesto no lugar antigo) — consertadas em `3a6d22c` (rc=0 isoladas). **3 passam isolados com rc=0** (fio 50 ok · agendador 78 ok · `test_o_vocabulario_viaja_na_imagem` 40 verdes): falharam com a bateria rodando JUNTO com a confirmação e os documentos (§11). **1** (`test_CONTROLE_o_harness_CONSEGUE_restaurar_rubrica`) falhou no meio e deixou a mutação de controle do harness em `backend/scripts/rubrica.py`; restaurada por cópia. ⚠️ 2ª rodada PARCIAL, só de `test_todos_os_guardas_script_rodam.py`: 13 failed · 292 passed, 3 nomes fora da base e DIFERENTES dos da 1ª — 2 passam isolados, o 3º era o guarda acusando a mutação vazada. INFERÊNCIA: arquivo instável sob carga → **P-E0018-30**. A linha de base NÃO foi alterada — triagem **NOMINAL** contra `reports/BATERIA-LINHA-DE-BASE.txt` (📊 **35 failed** em
21/09). Rodadas nesta SPEC: **1 inteira + 1 parcial de um arquivo** (a contagem de rodadas sai do `.diario-da-bateria.jsonl`).
⚠️ A bateria rodou **depois** do conserto, como manda o rito.

```
{PUSH}
```

## 13. Telemetria (protocolo §11) — `python scripts/medir_execucao_claude_code.py --sessao atual`

```
📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual`, 21/09/2026 (antes da entrega; o fecho não entra):
```
EXECUTOR (sessao principal) 05:46 381 min turnos 86 pico 368k US$ 20.10 fable-5-1
· Digest pendências e decisões 05:48 2 min turnos 13 pico 72k US$ 0.78 opus-5
· Builder F1 cota rodízio contrapre 05:53 52 min turnos 77 pico 265k US$ 9.78 opus-5
· Builder F2 relógio do modelo 05:54 26 min turnos 75 pico 192k US$ 6.45 opus-5
· Builder F3 segurança dois tenants 06:22 34 min turnos 93 pico 245k US$ 9.81 opus-5
· Builder F4 líder e costura 06:49 35 min turnos 84 pico 252k US$ 9.30 opus-5
· Builder F5 relógio e Central 07:01 59 min turnos 93 pico 247k US$ 10.01 opus-5
· Builder F6 costura final 08:04 31 min turnos 74 pico 232k US$ 7.99 opus-5
· Juiz fresco EXTRA-001.8 08:37 24 min turnos 63 pico 227k US$ 5.63 fable-5-1
· Red team EXTRA-001.8 08:38 16 min turnos 51 pico 226k US$ 4.65 fable-5-1
· Builder do conserto único 09:03 89 min turnos 201 pico 405k US$ 30.97 opus-5
· Confirmação do conserto 001.8 10:39 7 min turnos 26 pico 127k US$ 2.26 fable-5-1
· Agente de documentos 001.8 10:48 43 min turnos 108 pico 487k US$ 22.23 opus-5
TOTAL agentes alem do executor: 12 . turnos 1044 . ctx 222.9M . saida 0.33M . US$ 139.95
```
```

📊 **Achados por mecanismo, com EXCLUSIVO** (já medido, §5): juiz 1 exclusivo · red team 2 exclusivos · conserto
1 · confirmação 1 (resíduo) · 2 achados pelos dois laudos · canário: **NÃO RODOU**.
**Notas:** juiz **76/100** · red team **78/100** · confirmação **86/100** ·
**nota da execução: 85/100** — critério em uma linha: defeitos materiais mortos antes do
push, com guarda novo e linha de controle para cada um, e o canário ainda por rodar.
