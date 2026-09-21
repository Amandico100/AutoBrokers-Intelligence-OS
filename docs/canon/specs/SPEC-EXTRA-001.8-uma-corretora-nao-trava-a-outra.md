# SPEC-EXTRA-001.8 — UMA CORRETORA NÃO TRAVA A OUTRA
## Cota por corretora · rodízio · teto por chamada e por turno · contrapressão que não perde mensagem

> **Status:** **EXECUTADA em 21/09/2026** · **CANÁRIO PENDENTE** (ação do Founder — §11/§14).
> **Versão:** 2.0, convertida da proposta de 13/09/2026 (62 KB) · **Rito:** AAA v13.1.
> **Branch:** `feat/spec-extra-001.8-isolamento-por-corretora` · **Base:** `bfa0a40`
> **Relatório:** [`reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md`](../reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md).
> **Origem:** P-PILOTO-01 · D-PILOTO-07 · D-FILA-01. **Depende de:** a trava de turno da EXTRA-001.2 §5, que
> 📊 já estava na árvore no BLOCO 0.
>
> ⚠️ **O que a conversão mudou:** todo número que a execução desmentiu foi trocado pelo **valor medido**; o
> `RESEARCH-PACK` que a proposta citava **não existe no repositório** e o BLOCO 0 (§4) remediu tudo; os rótulos
> de rito da proposta ("opção B", "3 juízes", "laço curto") são históricos e saíram. ⛔ **Nenhum nome de
> corretora ou de pessoa aparece aqui** (CLAUDE.md §13.9): a prova é com **duas corretoras de teste**.

---

## 0. Resultado e motivo

> Quatro segurados de uma corretora e quatro de outra falam ao mesmo tempo, e os oito são atendidos. Se o modelo
> de uma ficar lento, se o portal dela travar ou se um número mandar cinquenta mensagens seguidas, **a outra não
> sente nada** — e nada se perde: o que não cabe agora espera, com uma linha dizendo por quê.

📊 **O defeito nunca foi observado em produção — foi lido no código** (os pilotos mediram ~1h53 de agente ligado
em 3 dias e 5 segurados, nunca duas corretoras juntas). Isso muda o gate: a prova não é "não aconteceu
de novo", é **uma corretora travada de propósito, medida contra a outra**. 🔴 E é CRÍTICO sem incidente porque
P-PILOTO-01 registra o custo, palavra do Founder — *"com centenas de corretoras, um travamento em uma para todas
— irreparável"*. Isolamento não avisa: aparece no primeiro dia em que o produto dá certo.

**Decisões do Founder que são lei aqui:** **D-PILOTO-07** → **4 é o PISO da cota** e "nenhuma interferência"
vira número medido (§5.4) · **D-PILOTO-02** → conversa pausada não ocupa cota (§6.4) · **D-FILA-01** → as duas
pendências de isolamento ≥ 90 entram nesta SPEC (§9.5).

### 0.1 EXECUTION CARD — confirmado no BLOCO 0

```text
OUTCOME ....... 4+ atendimentos simultâneos POR CORRETORA; uma corretora lenta, travada ou em rajada
                não muda a latência da outra; zero mensagem perdida
RISCO 8 (alcance 3 · reversibilidade 3 · frequência 2) · SUPERFÍCIE 2 · NÍVEL CRÍTICO
PISO .......... §3.2 "qualquer coisa que ENVIE" + "o filtro company_id"; o piso já daria CRÍTICO
O FIO ......... webhook → buffer (Redis) → varredura → cota do escopo → teto global → trava de turno
                → get_and_clear → grafo/modelo (com teto e disjuntor) → envio → payload.turn no banco
                → Central por corretora
UNIDADES ...... 7 (A medição · B cota+rodízio · C teto/retry/disjuntor · D contrapressão · E processos
                e líder · F observabilidade · G prova)
COESÃO ........ `buffer_processor.py` é ARQUIVO-HUB (A, B, D, F): um dono por vez; `llm_factory.py` é
                o hub de C. PARALELISMO REAL: 2 escritores, com arquivos disjuntos
TIME .......... builders Opus 5 · juiz Fable ‖ red team Fable (cegos, uma vez) · confirmação
REFERÊNCIA .... interna `app/workers/smith_worker.py:252-278` (a cota por tenant que JÁ existe em
                produção) + `tests/test_midia_e_concorrencia_do_webhook.py:519` (controle herdado) ·
                externas: §17 E1–E3
GATES ......... G1–G10 (§12) + S1 · S3 · G11 · costura 6–8 · cenário (k) · [6]
O ELO ......... §0.2 · FAIXA DE RELÓGIO declarada 💭 8–12 h · o card inteiro está no relatório §0.0
```

🔴 **BLOCKER nesta SPEC:** qualquer achado em que **uma corretora muda o que a outra recebe** — latência,
silêncio, mensagem perdida ou duplicada, **ou número atribuído à corretora errada**. É isolamento (CLAUDE.md §7)
e **não se rebaixa a pendência**. Nome de variável, formato de log e tela são pendência.

### 0.2 🔴 O ELO — onde uma corretora alcança a outra

```
① SEMÁFORO DE 6 GLOBAL com a CONFERÊNCIA BARATA DENTRO (buffer_processor.py:77-81): o GET de
   prontidão (~1 ms) fica atrás de até 6 turnos de LLM — com 4 conversas de uma corretora em voo a
   10 s, a da outra NEM É OLHADA. Não é "esperar a vez", é "não existir para o varredor".
② A LISTA É UMA SÓ — 📊 zero `sort`, zero agrupamento, zero rodízio: a ordem do SCAN, arbitrária.
③ O RELÓGIO NÃO EXISTE — 📊 B0.2 e B0.3: zero linhas. Uma chamada pendurada segura 1 dos 6 slots
   até o SDK desistir, e quem decide é o SDK.
④ O POÇO DE THREADS É UM SÓ — 📊 B0.4: com 1 vCPU são 5 threads para TODAS as corretoras.
⑤ ⚠️ NÃO ENTRA: o rate limit do webhook é por IP (balde de ENTRADA) → P-E0018-23 (§18).
```

---

## 1. Escopo, e a autorização de testes

🔴 TESTE-A e TESTE-B vêm da allowlist privada do Founder e entram nas evidências por **alias**; ⛔ nenhuma
mensagem a segurado, seguradora, atendente ou grupo real, nenhum número operacional como remetente, nenhuma carga
contra API de LLM, Evolution ou portal, nenhuma PII impressa. 🔴 **Os dois números têm de estar em CORRETORAS
DIFERENTES ao mesmo tempo** — na mesma corretora o canário não prova nada (§14).

**Obrigatório:** (1) **medir** a latência por etapa e os recursos do §0.2; (2) **cota por corretora + rodízio** no
processador atual, sem fila nova; (3) **teto por chamada e por turno**, retry só em erro transitório, **disjuntor
por provedor de LLM**; (4) **contrapressão** — cota cheia, a mensagem espera, nunca se perde nem expira em
silêncio, e o dono é avisado; (5) **lock de líder** em Redis para os jobs do APScheduler; (6) **observabilidade
por corretora** na Central de Agentes; (7) **prova** com duas corretoras, uma travada de propósito; (8) 🔴 **as
duas pendências de isolamento da D-FILA-01** (§9.5). O que ficou fora está no §18, com o gatilho de retorno.

---

## 3. Autoridades preservadas e arquitetura

🔴 **CLAUDE.md §5 proíbe criar em paralelo runtime, scheduler ou executor.** Esta SPEC não cria nenhum: **parte**
o que já existe. O processador de buffers é **estendido** (cota por escopo, rodízio, teto por conversa, mesma
assinatura com defaults); a chave `whatsapp_buffer:{escopo}:{telefone}` já isolava **dado** e passa a
**escalonar**; a cota **copia a forma** — não o código — da que o worker de Work Runs roda em produção
(`app/workers/smith_worker.py:252-278`); a fila com consumer group (`services/work/queue.py`) é **lida e
rejeitada** (§6.1); o lock de líder copia o padrão de `portal_worker/leases.py`; a fábrica de LLM **recebe**
`timeout`/`max_retries`; a Central **ganha um bloco por corretora**; e a trava da 001.2 é **pendurada**.

```text
SCAN whatsapp_buffer:*  →  MGET em lote: quais estão prontas   (§5.2, a conferência sai do semáforo)
  → agrupar por ESCOPO e intercalar (§6.2)  → cota[escopo] → teto global (§6.3, a ordem é a regra)
  → trava de turno da 001.2 (por conversa)  → get_and_clear (GET+DEL atômico)
  → processar COM TETO DE TEMPO (§7.2)      → messages.payload.turn (§5.1)
```

Supabase é a verdade durável; Redis é trânsito, lease e cache. Nenhuma fila, publisher ou scheduler novo. 🔴
**Zero migration.** 🔴 **A cota vem ANTES da trava de turno**: depois, uma conversa esperando a trava ocuparia um
slot de cota da corretora — e a 001.2 teria criado, dentro da 001.8, o gargalo que a 001.8 existe para matar.

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código

> **Este documento envelhece. O número do executor vence.** ⚠️ A proposta mandava rodar "as 16 premissas do
> RESEARCH-PACK §2". 📊 **O RESEARCH-PACK não existe.** Abaixo, o que foi medido em **21/09/2026**.

| # | 📊 medido, e a consequência | comando |
|---|---|---|
| B0.1 | semáforo global de 6 com `should_process` **dentro** dele (o elo ①) | leitura `buffer_processor.py:77-81` |
| B0.2 | **0** linhas de `wait_for`/`timeout` no processador → o teto do turno nasce aqui | `grep -n "wait_for\|timeout" .../buffer_processor.py` |
| B0.3 | **0** linhas de `timeout`/`max_retries` na fábrica → o teto por chamada nasce aqui | `grep -n "timeout\|max_retries" .../llm_factory.py` |
| B0.4 | ⚠️ **326** `asyncio.to_thread` (proposta: 306) · **0** `set_default_executor` → o poço vira explícito | `grep -rn "asyncio.to_thread" app/ \| wc -l` |
| B0.5 | `BUFFER_TTL_SECONDS = 60`, dois pontos de escrita — é o defeito da §8 | `core/config.py:75` · `message_buffer_service.py:463,622` |
| B0.6 | ⚠️ **25** jobs registrados (proposta: 24), classificados um a um (§9) | `grep -c "scheduler.add_job" .../buffer_processor.py` |
| B0.7 | a trava de turno da 001.2 **já está na árvore** → o "plano B" da proposta cai | leitura de `abrir_turno`/`fechar_turno` |
| 🔴 B0.8 | **ACHADO:** `check_buffers` roda a cada 1 s com `max_instances=10` e **cada varredura criava o SEU `Semaphore(6)`** → o teto real chegava a **60** e uma cota local viraria **40**; por isso o estado de admissão passa a viver **no MÓDULO** | leitura + medição |
| B0.9 | produção, n=**41** turnos do **chat do painel**, 09/09–17/09: mediana **39.133 ms** · p95 **107.047 ms** · máx **135.585 ms**. É **TURNO**, não chamada única → ⚠️ **"p95×3" NÃO vale para o teto por chamada**; amostra pequena, declarada | `SELECT count, percentile_cont(.5/.95), max` sobre `payload->'turn'->>'total_ms'`, `status='complete'` |
| ⛔ B0.10 | **NÃO MEDIDO:** `cpu_count` do contêiner implantado — caixa do Founder (P-E0018-02); o poço já é ≥ 32 por default | sem acesso ao contêiner |

**GATE B0** ✅ matriz com valor de hoje e comando ao lado; o não medido declarado. **MUTAÇÃO B0:** *"o semáforo
de 6 já é por corretora, porque a chave tem o escopo"* → refutado com a linha `:77` — a chave isola **dados**,
não **vez na fila**.

---

## 5. BLOCO A — a medição, antes de qualquer conserto

**5.1 O relógio do atendimento passa a existir, no vocabulário que já existe.** 📊 O turno era registrado só
no chat do painel; o atendimento não gravava nada.

```python
payload["turn"] = {"status": "complete"|"failed"|"timeout"|"adiado",   # ⚠️ o chat diz `complete`
                   "total_ms": int,
                   "stages": [...],          # ⚠️ mesmo nome E MESMO TIPO do chat (lista de texto)
                   "stage_ms": {"buffer_espera", "fila_cota", "grafo", "envio"}}   # chave NOVA
```

⛔ **Não criar um segundo vocabulário:** os tempos por etapa entram numa chave **nova** em vez de mudar o tipo de
uma existente (CLAUDE.md §12.1 — conserta-se o campo, não o texto). 📊 O UPDATE é por `id` + `conversation_id`,
**depois do envio**, em `try` próprio: não vira "falha técnica" e não corre com outro escritor (📊 é o único
`update` de `messages` no backend). ⚠️ `provedor` e `modelo` ficaram fora → P-E0018-11.

**5.2 A conferência de prontidão sai de dentro do semáforo.** `_esta_pronta` extrai a regra de debounce **sem
mudar comportamento**; `should_process` fica (a 001.2 o chama) e delega; `prontas(chaves)` faz **um `MGET`**.
⛔ `prontas` **não consome**: `get_and_clear` continua o único consumidor.

**5.3 O teste de carga.** `tests/test_uma_corretora_nao_trava_a_outra.py` exercita `processar_buffers_prontos` —
**o motor**, por AST do arquivo em disco, dublê só na borda: DOENTE 50 chaves dormindo 10 s · SADIA 4 chaves,
0,2 s · mede até a última SADIA · **CONTROLE** é a mesma rodada sem a doente. ⚠️ **A linha de controle é
obrigatória** (CLAUDE.md §9.2): sem ela um ambiente rápido passaria por acaso.

**5.4 🔴 O X do gate G3 — medido, não palpitado.** 📊 O projeto não tinha SLO declarado.

```
p95 da SADIA com a DOENTE  ≤  p95 da SADIA sozinha + X      X = max(PISO, p95 sozinha × 0,25)
PISO FINAL = 0,120 s       comando: python tests/test_uma_corretora_nao_trava_a_outra.py --so G3
```

⚠️ **O piso subiu de 0,050 s para 0,120 s no conserto**, declarado: com 0,050 s o G3 **piscava** no relógio do
Windows (1 vermelho em 6 rodadas), e um gate que pisca ensina a ignorá-lo. 📊 **Antes:** p95 sozinha 0,0012 s ·
com a doente 0,0215 s · CONTROLE com a cota desligada 2,4554 s. 📊 **Depois, 10 rodadas:** com a doente
0,0211–0,0294 s · CONTROLE 4,84–4,95 s · **10/10 verde** — o controle fica ~200× acima do medido, e é ele que dá
direito à conclusão.

**GATE A** (gate e mutação de cada guarda: §12): o turno aparece em `payload.turn` com `total_ms` e `stage_ms` ·
`prontas()` concorda com `should_process` · o teste de carga imprime os dois p95 e o controle.

---

## 6. BLOCO B — a cota por corretora e o rodízio

| opção | nota | por quê |
|---|---|---|
| **cota por corretora + rodízio no processador atual** | **91** | reaproveita o motor, preserva o teto global, garante o piso de 4 **e** que a vez chega. É a forma que o worker de Work Runs usa em produção e que a k8s APF (§17 E2) implementa em escala |
| pool POR corretora, sem teto global | 62 | dá isolamento e tira o teto: N × 4 estoura o event loop e o poço do §0.2 ④ |
| **fila nova em Redis Streams por corretora** | **45** | ⛔ **motor paralelo:** o buffer **já é** a fila e o `GET+DEL` em pipeline **já é** a entrega única |
| subir o paralelismo de 6 para 24 sem cota | 30 | mais slots para quem já monopoliza: o mesmo defeito, mais caro |

🔴 **A lição que o repositório já pagou:** o worker de Work Runs recusa a mensagem quando o tenant está no teto
e **não dá `ack`** — a entrada só volta por tempo de ocioso. A nossa cota não herda isso: o buffer fica no Redis
e a varredura de 1 s o reencontra.

```python
escopo_da_chave("whatsapp_buffer:{escopo}:{telefone}") -> escopo
#   🔴 chave malformada, escopo vazio ou `sem-integracao` → "" (fail-closed)
_COTA_PADRAO = 4    _PARALELISMO_PADRAO = 6 (legado/dublê)    _PARALELISMO_COM_COTA_PADRAO = 24
ordenar_em_rodizio(chaves)  # A1 B1 C1 · A2 B2 C2 … determinística: dentro do escopo, ordem recebida;
                            # entre escopos, ordem estável. ⛔ nem aleatório nem por tamanho de fila
escopo vazio      -> _adiar(chave, "sem_escopo")      # fail-closed
sem vaga na cota  -> _adiar(chave, "cota")            # (1) NAO-BLOQUEANTE
async with teto_global:                               # (2) bloqueante
    token = abrir_turno(escopo, phone)                # (3) trava da 001.2, por conversa
    if token is None: -> _adiar(chave, "turno")
    try:     get_and_clear_buffer(chave) -> wait_for(processar(...), TETO_DO_TURNO)   # 7.2
    finally: fechar_turno(escopo, phone, token)
```

📊 **Dois defaults de paralelismo** (nota 85 × editar o guarda herdado 70): o legado fica em 6 para que
`test_midia_e_concorrencia_do_webhook.py:519` continue verde **sem edição**; produção usa 24. 🔴 **O estado de
admissão vive no NÍVEL DO MÓDULO** (nota 92) — cada varredura criava o seu próprio semáforo (B0.8), e estado
local à chamada não é teto nenhum. 🔴 **A cota é NÃO-BLOQUEANTE** (nota 92 × semáforo por corretora 48): quem não
tem vaga **adia**, e o `adiar` só faz `EXPIRE`; o teto global segue bloqueante (90). 🔴 Os contadores por escopo
**somem quando zeram** — dicionário que só cresce é vazamento com nome de isolamento.

**6.4 O que NÃO ocupa cota:** conversa **pausada por intervenção humana** (D-PILOTO-02) e conversa em **janela
de silêncio** — esta SPEC não move a decisão de silêncio (é da 001.2/001.3), mede. 📊 A chave `sem-integracao` é
**adiada SEM renovar vida** (nota 90): ela já não era respondida, e renovar a vida de quem ninguém vai atender é
guardar lixo para sempre.

**GATE B.** 50 chaves de A + 4 de B pelo motor real: as 4 terminam dentro de X · rodízio intercalado e estável ·
`sem-integracao` adiado e não processado · **o teste de paralelismo existente continua verde**.

---

## 7. BLOCO C — o relógio do modelo e das ferramentas

**7.1 Teto por chamada, na fábrica.** `LLM_TIMEOUT_SEGUNDOS` e `LLM_MAX_RETRIES` entram nos **quatro**
construtores; 📊 antes a fábrica não passava nenhum dos dois e o SDK aplicava um default que não escolhemos nem
medimos. ⚠️ **O teto NÃO nasce de "p95 × 3"** (= 321 s pelo B0.9): o p95 medido é de **TURNO**, não de
**chamada**, e a régua errada daria um teto três vezes maior que o turno inteiro. **Decisão: 90 s por chamada**
(nota 85 × "p95×3" 40).

**7.2 Teto por TURNO, e a inequação que o conserto escreveu.**

```
ATENDIMENTO  wait_for(processar(...), timeout=WHATSAPP_TURNO_TIMEOUT_S) · TETO = 300 s (a construção pôs
   180 s; o conserto subiu). INEQUAÇÃO GUARDADA: teto_por_chamada × (retries+1) < teto_do_turno →
   90×3 = 270 < 300. Com 180 s o corte vinha ANTES do erro final do SDK: o disjuntor nunca abria no
   caso que lhe dá nome, e a conversa era consumida e cortada em silêncio.
CHAT DO PAINEL (SSE)  ⛔ NADA de `wait_for` total em volta do `astream_events`: turno que EMITE delta
   não está travado, e cortá-lo é regressão da SPEC-096. Entrou um guarda que PROÍBE esse `wait_for`.
```

🔴 **O corte NÃO devolve a rajada ao buffer** (88 × devolver 45): depois do `get_and_clear` não há como saber se
o envio saiu, e devolver seria risco de **resposta duplicada**. 🔴 **E não vira silêncio:** `wait_for` cancela com
`CancelledError`, que **não é `Exception`** — o fallback honesto do webhook (`except Exception`) **não rodava**.
Entrou um `except asyncio.CancelledError` que, se ainda se pode falar e nada foi enviado, manda o mesmo aviso
com `asyncio.shield(...)` e **re-levanta**.

**7.3 Retry só no que é transitório.** Timeout, conexão, 429 e 5xx tentam de novo com full jitter
`random(0, base·2ⁿ)`, base 2 s, teto 30 s, 2 voltas; ⛔ 400/401/403/404, chave inválida e modelo inexistente
falham na hora. 📊 **Medido:** os SDKs já **não repetem** esses códigos (`openai/_base_client.py:821-862`,
`anthropic/_base_client.py:842-874`) → nenhum 2º laço de retry por cima.
🔴 **401 NUNCA abre o disjuntor**, e a razão é o isolamento: a chave de API hoje é **GLOBAL**; no dia em que for
por corretora, um 401 de uma fecharia o provedor para todas — está escrito ao lado da regra.

**7.4 Disjuntor POR PROVEDOR.** Chave `llm_breaker:{provedor}`; fechado → aberto → meio-aberto; abre com N falhas
não-transitórias ou N timeouts numa janela; no meio-aberto passa **UMA** chamada. 🔴 **Por provedor, não por
corretora:** um provedor cair é fato do mundo, e um disjuntor por corretora abriria N vezes para o mesmo fato.
🔴 **A costura, que a construção quase esqueceu:** ele só serve se **alguém perguntar antes de consumir o
buffer** — desenho escolhido (nota 90): *"algum provedor barrado? só então resolve escopo→provedor, com cache de
`ISOLAMENTO_PROVEDOR_CACHE_S`"*, e varredura sem provedor barrado não paga nada. 🔴 **Aberto não vira silêncio:**
a mensagem é **retida** (§8), o dono é avisado, nada chega ao segurado. ⚠️ A sonda do meio-aberto foi escrita e
**ninguém a chamava**: 📊 **8** conversas eram consumidas de uma vez (controle, disjuntor aberto: **0**).

**7.5 As ferramentas também.** 📊 Já tinham teto (InfoCap 8–15 s, Evolution 20–30 s, visão 30 s, subagente 30 s);
4 clientes `httpx.AsyncClient()` não tinham nenhum. Contrato: teto default para todo cliente do backend e um
guarda que conta **zero** sem `timeout` — 📊 **47 varridos, 0 sem teto**.

**GATE C.** os 4 construtores recebem `timeout`/`max_retries` (kwargs reais) · `wait_for` no atendimento e
**nenhum** em volta do `astream_events` · backoff com jitter · 401 fora do backoff · o disjuntor abre na 5ª e a
6ª não sai · zero `httpx` sem timeout · 🔴 a inequação do §7.2 é **guardada**.

---

## 8. BLOCO D — contrapressão: a mensagem espera, nunca se perde

**8.1 O defeito que a contrapressão descobre: o buffer EXPIRA.** 📊 `BUFFER_TTL_SECONDS = 60`, desde a última
escrita: com a cota cheia e 50 conversas na frente **uma conversa pode esperar mais de 60 s, e o Redis apaga o
buffer** — o segurado escreveu, o webhook respondeu `buffered`, e a mensagem sumiu **sem uma linha em lugar
nenhum**. Já era verdade antes da cota; a cota o torna alcançável. Por isso `adiar` **renova o TTL (EXPIRE) e
conta a espera do escopo**, ⛔ sem reescrever o conteúdo — mexer em `last_at` remataria o debounce e a rajada
nunca fecharia. `motivo` é uma de quatro palavras (`cota` · `turno` · `breaker` · `sem_escopo`), e a conta que
fecha é `vistas`, `prontas`, `processadas`, `adiadas{...}`, `falhas`, `timeouts`, `expiradas`.

🔴 **`expiradas` tem de ser ZERO, e o G7 o afirma:** é o único número desta SPEC que não admite "quase" — chave
pronta numa varredura e ausente na seguinte, sem ter sido processada, é mensagem de segurado perdida. 🔴 **E a
contabilidade é POR DONO — o defeito mais grave desta SPEC.** `expiradas` e `timeouts` eram totais **globais**,
gravados no hash de **cada** escopo presente: 📊 a perda de uma corretora aparecia na tela da outra, e o número
**multiplicava** por escopo ativo. O conserto conta por escopo e grava no hash **do dono**, mesmo sem mais nada
na fila (**G11**). ⚠️ Três contagens de perda que não era perda foram fechadas junto: turno cortado ou falho
recontado na varredura seguinte · mensagem absorvida por um turno em andamento · a chave passou a ser marcada
**consumida** no instante do `get_and_clear`, em vez de depender de um mapa que a varredura sobreposta apaga.

**8.3 A presença e o aviso ao dono.** A presença "digitando…" é contrato da EXTRA-001.2 §6.4 — ⛔ não
reimplementar; ⚠️ o gatilho no adiamento por cota **não foi implementado** → P-E0018-10. O **aviso ao dono** sai
**uma vez** por `ISOLAMENTO_AVISO_JANELA_S`, pelo caminho que a EXTRA-001.3 governa (nenhum destino ou canal
novo). 🔴 **Nasce DESLIGADO** e **não deve ser ligado antes de P-E0018-09**.

**GATE D.** 200 chaves, cota 4: **zero** `expiradas` · `adiar` renova o TTL sem alterar `last_at` · o aviso sai
**uma vez** por janela.

---

## 9. BLOCO E — processos, réplicas e o lock de líder

🔴 **Mais processos aumentam o TETO. Cota e rodízio produzem o ISOLAMENTO.** Este bloco impede que uma réplica
acidental **duplique** os jobs: **lock de líder + `SCHEDULER_ENABLED`, 1 processo — 88** (fecha o risco real e é
pré-requisito das outras) × serviço de jobs separado **84** (depende de 🧑 criar o serviço: fica pronto e
desligado) × `uvicorn --workers N` **41** (quebra memória de processo — P-096-STOP-MULTIPROCESSO).

```
SET autobrokers:scheduler:lider {token aleatório} NX EX 60   (renovado a cada 20 s)
EVAL <script literal da doc do Redis> — solta só se o valor ainda for o token. ⛔ Nunca DEL cego
não é líder → não inicia o agendador (/health: `seguidor`) · perdeu o lock → PAUSA e tenta de novo
Redis fora  → 🔴 FAIL-CLOSED para os jobs que ENVIAM; fail-open para os que leem/higienizam
```

📊 **Os 25 jobs foram classificados um a um** (B0.6). Duas decisões medidas: (a) a varredura do buffer fica
**FORA** do lock (92 × 38) — ela não envia por conta própria, e parar de varrer é pior que varrer duas vezes;
(b) perder a liderança usa `pause_job`/`resume_job` (93 × `shutdown`+`start` 22), porque 📊 no APScheduler
3.11.3 `start()` depois de `shutdown()` levanta `SchedulerAlreadyRunningError`. ⚠️ **P-238 é
AGRAVADA DE PROPÓSITO e declarada:** sem Redis os jobs que ENVIAM ficam fail-closed (o vigia incluído) — dois
avisos ao mesmo grupo pesam mais que o silêncio do vigia numa queda de Redis; **destrava** com a varredura lendo
a lista durável de work runs.

**9.3** `set_default_executor(ThreadPoolExecutor(max_workers=EXECUTOR_THREADS or max(32, cpu_count()+4)))` — 📊 o
piso passou a `max(32, cpu+4)` (nota 91), porque o default dependia do `cpu_count` do contêiner, que ninguém
conhece (B0.10): com 1 vCPU seriam **5 threads** para 326 pontos de `to_thread`. `/health` publica
`executor_threads`.

**9.4 `max_instances`.** ⚠️ **O teto real era 10, não 24:** cada varredura vive enquanto os turnos dela vivem, e
com 10 em voo o APScheduler **pula** as seguintes — enquanto pula, **ninguém novo é atendido e ninguém renova o
TTL de 60 s de quem espera**. 📊 Com o agendador REAL: com `max_instances=10` a 4ª corretora esperou **3,32 s**
(= 17 "segundos" do produto); com 100 (controle), **0,15 s**. 🔴 Conserto: `max_instances` = teto global + folga
(**24 + 16 = 40**), 82 × redesenhar a varredura para não esperar os turnos 75 (certo para escala, grande demais
para um conserto → **P-E0018-06**). 📊 `coalesce` e `misfire_grace_time=1` já eram default e impedem avalanche.

**9.5 🔴 As duas pendências de isolamento da D-FILA-01.** **P-098-MCP-ROTAS-SEM-COMPANY:** a cerca passou para
**DENTRO do serviço MCP** — ele confirma o agente da corretora e age com **id + agent_id** (nota 92 × coluna
`company_id` nova 41 × só RLS 35); id alheio responde **404**, não 403 (nota 84 × 78 — 403 confirma existência).
Gate **S1**, dois tenants. **P-E00151-09:** nome de pessoa real **sai do dado global de corredor** (o campo que
entra no prompt de TODAS as corretoras) e de 23 comentários. Gate **S3**: nome por hash, dado semeado **0**.

**9.6** `smith-api` recebe as variáveis novas (§16), **todas com default no código**, e continua com **1**
réplica; o serviço de jobs separado (🧑, opcional) usa a mesma imagem com `SCHEDULER_ENABLED=true` e a API passa
a `false`. ⛔ **Nenhum valor de variável nesta SPEC nem no relatório. Só o NOME.**

**GATE E.** dois processos: **um só** inicia o agendador · matar o líder → o seguidor assume em ≤ TTL · sem Redis
nenhum job de **envio** roda · `EXECUTOR_THREADS` é lido.

---

## 10. BLOCO F — a Central de Agentes passa a ver por corretora

📊 A Central respondia *"o agente X produziu?"*, nunca *"a corretora Y foi atendida em quanto tempo?"*. Entra um
bloco no MESMO JSON do endpoint existente:

```json
"atendimento_por_corretora": [{"company_id", "nome", "em_execucao", "em_espera", "cota", "p95_ms_24h",
  "mediana_ms_24h", "ultimo_motivo_de_espera", "expiradas_acumuladas", "breaker": {"<provedor>": "fechado"}}]
```

⚠️ **`expiradas_acumuladas`, não `expiradas_24h`** (nota 92): um `HINCRBY` com TTL renovado **não é** janela
deslizante, e chamar de "24h" o que não é de 24 h é o campo que mente sobre o que guarda (CLAUDE.md §12.1).
Fontes, todas existentes: os contadores Redis do §8.2, p95/mediana de `payload.turn.total_ms` cruzado com
`conversations.company_id`, e o estado do disjuntor. Frontend: **uma seção nova na página que existe**, sem tela
nova; só contagens, estados, ids e tempos. ⚠️ É o número que o Founder deve olhar todo dia.

**GATE F.** o bloco traz dois `company_id` distintos e bate com os contadores · a rota continua só para
administrador da plataforma e nenhum `company_id` alheio vaza · `next start` + uma requisição respondendo.

---

## 11. BLOCO G — a prova: duas corretoras, uma travada de propósito

**11.1** `_atraso_de_teste_ms(company_id)` é **fail-closed**: lista vazia = ninguém, fora da allowlist → 0 e não
dorme. ⛔ Em produção a allowlist fica vazia, e **G10 exige que o default produza ZERO atraso**.

**11.2 Os seis casos do canário — 🔴 NÃO RODARAM.**

| # | o quê | o que prova |
|---|---|---|
| 1 | **antes**: TESTE-A na corretora 1 manda 3 mensagens; medir `total_ms` | a linha de base, sem doente |
| 2 | **durante**: corretora 2 com atraso alto + 20 conversas sintéticas e, **ao mesmo tempo**, TESTE-A manda 3 | 🔴 **o gate**: caso 2 ≤ caso 1 + X (§5.4) |
| 3 | TESTE-B na corretora 2 (a doente) manda 1 mensagem | é atendido, **lento mas atendido**: `adiado`/`cota`, nunca `failed` |
| 4 | rajada de 50 mensagens de TESTE-B em 30 s | entrada = saída + retidas; `expiradas` = **0** |
| 5 | disjuntor aberto na corretora 2 (provedor em host inválido) | a 1 **não sente**; o dono da 2 recebe **um** aviso; nada ao segurado |
| 6 | **depois**: allowlist esvaziada; repetir o caso 1 | o produto voltou ao normal — o mesmo número do caso 1 |

🧑 **Só o Founder:** parear TESTE-A e TESTE-B em duas corretoras de teste distintas; ligar e desligar as
variáveis do canário; clicar Implantar. **GATE G** ⛔ **PARCIAL NOMEADO — não rodou** (P-E0018-01).
**MUTAÇÃO G.** rodar o caso 2 com a cota desligada → o gate fica **vermelho**: é a única prova de que ele
consegue ficar vermelho.

---

## 12. Guardas e mutações

Todos sobre o **MOTOR** e o **ACERVO real** (CLAUDE.md §9.4).

| # | guarda (todos ✅ verdes) | a mutação que o deixa VERMELHO |
|---|---|---|
| **G1** | `prontas()` e `should_process()` concordam sobre 20 buffers do corpus | régua própria em `prontas` |
| **G2** | `ordenar_em_rodizio` intercala e é determinística | devolver a ordem do SCAN |
| **G3** | 50 chaves de A + 4 de B → as 4 dentro de X, **com controle** (10/10) | cota altíssima |
| **G4** | a cota é adquirida **antes** do teto global | inverter a ordem |
| **G5** | o teste de paralelismo herdado continua verde, **sem edição** | chave da cota sem o escopo |
| **G6** | os 4 construtores com `timeout`/`max_retries`; 47 `httpx` varridos, 0 sem teto | tirar `timeout` de um |
| **G7** | 🔴 200 chaves, cota 4: `expiradas == 0` e entrada = processadas + adiadas | `adiar` vira `pass` |
| **G8** | não-líder não inicia o agendador; sem Redis nenhum job de **envio** roda | fail-open no vigia |
| **G9** | 401 fora do backoff; o disjuntor abre na 5ª e fecha depois de T | backoff no 401 |
| **G10** | 🔴 sem a allowlist, o atraso é **ZERO** para qualquer `company_id` | default virar "todos" |
| **S1** | 🔴 a cerca de corretora do MCP, **dois tenants**; id alheio → 404 | tirar o filtro de agente |
| **S3** | 🔴 nome próprio por hash no dado global; dado semeado = 0 | repor o nome no campo global |
| **G11** | 🔴 **contabilidade POR DONO**: a perda no hash de quem perdeu, nunca na vizinha | contar global e gravar em todo escopo ativo |
| **costura 6–8** | a espera chega ao webhook · o resumo da varredura é **por corretora** · o aviso ao dono está ligado ao processador (flag desligada) | desligar a costura |
| **cenário (k)** | 🔴 **o AGENDADOR REAL** com turnos longos: a 4ª corretora é olhada | `max_instances` de volta a 10 |
| **[6]** | 🔴 corte do teto de turno **sem silêncio**: o aviso honesto sai | tirar o `except CancelledError` |

⚠️ **G3, G5 e G10 não se negociam** (o outcome · a linha de controle herdada da 001.2 · a trava do mecanismo
perigoso). Mutação restaura por **CÓPIA**, nunca `git checkout`; a bateria não roda enquanto um juiz muta.

🔴 **A maior lacuna do julgamento:** nenhum guarda rodava **o agendador REAL** com turnos longos — por isso o
teto de 10 instâncias atravessou 9 guardas verdes. É o CLAUDE.md §9.4 um andar acima (testou-se o motor, não quem
o chama), e o **cenário (k)** nasceu disso.

## 13. Migrations — **nenhuma** · e o canário, a entrega e o rollback

📊 Zero SQL, zero DDL, zero backfill: o turno em `messages.payload` (jsonb, o chat já grava `turn` ali) ·
contadores, lock de líder e disjuntor em Redis · a Central no JSON do endpoint existente.

**Antes:** TESTE-A e TESTE-B, cada um na **sua** corretora de teste, sem tocar QR operacional, com os bloqueios
provados por saída simulada. **Durante:** os seis casos da §11.2. **Depois:** esvaziar a allowlist do atraso,
repetir o caso 1 e mostrar que o número voltou; logs sem PII. ⛔ **Estado em 21/09/2026: PARCIAL NOMEADO** — o
canário **não rodou** (exige Implantar e dois números pareados em corretoras distintas, CLAUDE.md §10-5).
**Ausência de canário nunca vira verde.**

**Implantação:** `smith-api` → `smith-web` (o portal-worker não muda). **Rollback em 3 variáveis:**
`WHATSAPP_COTA_POR_CORRETORA` muito alta (a cota deixa de morder) · `LLM_TIMEOUT_SEGUNDOS = 0` (volta o SDK) ·
`SCHEDULER_ENABLED = true` em todas as réplicas. 🔴 Reverter código não desfaz mensagem enviada. ⚠️ Mexeu no
frontend: `npm run test:rotas-montam` + `next start` + **uma requisição** antes do gate verde (CLAUDE.md §9.1).
Marcos: gateado · na `main` (SHA e saída do push) · implantado (`/health` com `scheduler` e `executor_threads`) ·
🔴 canário **PENDENTE** · ativado em corretora operacional (🧑, fora desta execução).

## 14. As variáveis novas — SÓ O NOME

⛔ **Nenhum valor em documento.** Todas têm default: **o produto sobe sem o Founder definir nenhuma.**

```
WHATSAPP_COTA_POR_CORRETORA · WHATSAPP_BUFFER_PARALELISMO (já existia) · WHATSAPP_TURNO_TIMEOUT_S
LLM_TIMEOUT_SEGUNDOS · LLM_MAX_RETRIES · LLM_BREAKER_FALHAS · LLM_BREAKER_JANELA_SEGUNDOS ·
LLM_BREAKER_SEGUNDOS · LLM_BREAKER_MEIO_SEGUNDOS · LLM_BREAKER_SONDA_SEGUNDOS
HTTP_TIMEOUT_SEGUNDOS · HTTP_TIMEOUT_CONEXAO_SEGUNDOS · SCHEDULER_ENABLED · EXECUTOR_THREADS
ISOLAMENTO_PROVEDOR_CACHE_S · ISOLAMENTO_ATRASO_ALLOWLIST (vazia em produção) · ISOLAMENTO_ATRASO_MS
ISOLAMENTO_AVISO_AO_DONO (ausente = não avisa) · ISOLAMENTO_AVISO_ESPERA_S · ISOLAMENTO_AVISO_JANELA_S
```

`/health` ganha **`scheduler`** (`lider` | `seguidor` | `desligado` | `desconhecido`) e **`executor_threads`**.

---

## 17. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> Leitura de **13/09/2026**, reaberta na conversão.
### E1 — Microsoft · Bulkhead pattern — https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead
**Faz:** parte recursos por consumidor para que a falha de um não se propague; nomeia o nosso elo ④ (*"the
client's connection pool might be exhausted… the consumer's requests to other services are affected"*) e
recomenda, para partir consumidores, *"processes, thread pools, and semaphores"*, combinados com *"retry, circuit
breaker, and throttling"*.
**MODELAMOS:** ① **semáforo por consumidor** = a cota por corretora do §6, com o consumidor sendo o `escopo` da
chave do buffer; ② **thread pool dimensionado** = `EXECUTOR_THREADS` do §9.3 — a partição que o documento manda
fazer primeiro e que não existia.
**REJEITAMOS:** *"deploying them into separate virtual machines, containers, or processes"* como forma **desta**
SPEC: um contêiner por corretora é a granularidade que o próprio texto manda escolher com cuidado e que, com duas
corretoras de piloto, custa mais do que entrega. §18, com gatilho.
**Como o juiz inspeciona:** abre a página, confere que "Problems and considerations" cita semáforos e thread
pools, e compara com a cota por escopo e o `set_default_executor` no diff.

### E2 — Kubernetes · API Priority and Fairness — https://kubernetes.io/docs/concepts/cluster-administration/flow-control/
**Faz:** é a implementação de referência de **cota + fila justa** num sistema multi-inquilino real: o limite
global é *"divided up among a configurable set of priority levels"*, cada nível *"will only dispatch as many
concurrent requests as its particular limit allows"*, e dentro dele *"a fair-queuing algorithm prevents requests
from different flows from starving each other"*. O objetivo declarado é o nosso: *"a poorly-behaved [controller]
need not starve others"*.
**MODELAMOS:** ① **teto global repartido em cotas** = §6.3 (a cota da corretora **dentro** do teto do processo), e
é a razão de o "pool por corretora sem teto global" valer 62; ② *"a limited amount of queuing, so that no requests
are rejected in cases of very brief bursts"* → §8: a rajada **espera**, não é recusada nem perdida.
**REJEITAMOS:** ① **borrowing** (nível ocioso emprestar ao saturado) — com duas corretoras não paga, e emprestar é
a porta pela qual a interferência volta; ② **shuffle sharding** — resolve *quem divide fila com quem* quando há
mais inquilinos que filas; a nossa cota é nominal por `escopo` e não precisa de sorteio.
**Como o juiz inspeciona:** abre "Concepts" e confere que a nossa cota é subdivisão de um teto — e não um teto
novo por corretora — lendo a ordem de aquisição em `_uma`.

### E3 — Redis · `SET` (NX/EX) e o script de soltura — https://redis.io/docs/latest/commands/set/
**Faz:** documenta que `SET resource-name anystring NX EX max-lock-time` *"is a simple way to implement a locking
system with Redis"*, e prescreve as duas correções que o tornam honesto: *"set a non-guessable large random
string, called token"* e *"send a script that only removes the key if the value matches"* —
`if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) else return 0 end`.
**MODELAMOS:** o **lock de líder do agendador** (§9.2): token aleatório, `EX 60`, renovação a cada 20 s, soltura
pelo script literal. É o padrão que o worker de portais já roda em produção — reaproveitamos a forma, não
copiamos o arquivo.
**REJEITAMOS:** ① **Redlock** (que a própria página recomenda por cima do `SET NX`): temos **um** Redis, não N
independentes — Redlock sem N mestres é cerimônia sem garantia; ② **Redis Streams com consumer group** para o
atendimento (lido em https://redis.io/docs/latest/develop/data-types/streams/, mesma data) — o padrão já existe
no repo e serve Work Runs; trazê-lo para o WhatsApp criaria uma segunda fila sobre a mesma mensagem, o motor
paralelo do CLAUDE.md §5.
**Como o juiz inspeciona:** abre "Patterns" na página, compara o Lua do diff caractere a caractere com o da doc —
📊 foi comparado por máquina e é o literal — e confirma que não há `DEL` cego no caminho de soltura.

---

---

## 18. O QUE SAIU, E QUANDO VOLTA

| frente | por que não entra agora | gatilho de retorno |
|---|---|---|
| **executor de threads por caminho** | mudaria 326 chamadas de `to_thread`; o ganho é desconhecido antes de medir | o poço saturado sob a carga do §5.3 |
| **rate limit por corretora na ENTRADA** (hoje por IP) | a entrada não é o gargalo medido, e a chave certa é o `escopo`, só conhecido depois do auth | uma corretora estourar o balde (P-E0018-23) |
| **`uvicorn --workers N`** · **serviço de jobs separado** | 📊 P-096-STOP-MULTIPROCESSO (o registro de turnos é memória de processo); e o serviço novo depende de 🧑 | fechar P-096; o Founder criar o serviço |
| **a varredura deixar de ESPERAR os turnos** | certo para escala, grande demais para um conserto | ~10 corretoras saturadas, ou `max_instances` (40) virar o teto (P-E0018-06) |
| **borrowing entre corretoras** (E2) | com duas corretoras não paga, e é por onde a interferência volta | carga desigual medida em dezenas de corretoras |
| **Prometheus / OpenTelemetry** · **pool de banco por corretora** | 📊 zero instrumentação hoje e a Central resolve o instantâneo; o banco é service role com pool único | uma SPEC que precise de série temporal; saturação de conexões medida |
| **presença "digitando…" no adiamento por cota** · **disjuntor de portal** | o contrato da presença é da 001.2 e o gatilho não coube; o disjuntor de portal é da EXTRA-001.6 | P-E0018-10 · o de portal não volta |

🔴 **Nada do escopo obrigatório saiu em silêncio:** o que ficou está em `PENDENCIAS.md` como `P-E0018-01…29`,
com fato, o que destrava, dono e custo de esquecer.

## 19. Fila depois desta entrega, e definição de conclusão

`001.8 (esta) → 001.9 → 001.0 → triagem de pendências (D-FILA-01) → EXTRA-002`; a **EXTRA-001.10.1** entra
quando o Founder trouxer as capturas que faltam. Ficam prontos para quem vem depois: o `payload.turn` e o p95 por
corretora (a régua da 001.7) · a seção por corretora da Central (001.9) · a cota por `escopo`, que vale para
qualquer adaptador novo · o lock de líder, que deixa de ser decisão de cada job.

**Fechado:** card e BLOCO 0 no relatório · gates verdes e mutações vermelhas · paralelismo herdado verde ·
`expiradas == 0` e por DONO · bateria · `next start` + uma requisição · push colado · as 8 pendências re-julgadas
e as novas registradas · painel atualizado. **Aberto, e é do Founder:** 🔴 o canário em corretoras diferentes
(P-E0018-01) e a allowlist do atraso conferida vazia depois dele. 🔴 **Um item aberto = SPEC aberta.**
📋 A **caixa do Founder** desta SPEC está no relatório §8 e em `TAREFAS-DO-FOUNDER.md`.

> **Em uma frase:** a corretora com o modelo lento espera sozinha, e a pergunta *"perdi alguma mensagem hoje?"*
> passa a ter resposta — **zero**, e na corretora certa.
