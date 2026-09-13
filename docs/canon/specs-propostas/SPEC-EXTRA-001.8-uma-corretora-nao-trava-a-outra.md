# SPEC-EXTRA-001.8 — UMA CORRETORA NÃO TRAVA A OUTRA
## Cota por corretora · rodízio · teto por chamada · contrapressão que não perde mensagem

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline da pesquisa:** worktree `AutoBrokers-FIX`, HEAD `53a22c3`, `origin/main` em dia (📊 `git rev-list --count HEAD..origin/main` → 0). Todas as linhas citadas foram reabertas hoje; o BLOCO 0 as remede.
**Branch sugerida:** `feat/spec-extra-001.8-isolamento-por-corretora`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.8-uma-corretora-nao-trava-a-outra.md`.
**SPEC definitiva a criar:** `docs/canon/specs/SPEC-EXTRA-001.8-uma-corretora-nao-trava-a-outra.md`.
**Research Pack:** `SPEC-EXTRA-001.8-uma-corretora-nao-trava-a-outra-RESEARCH-PACK.md`.
**Relatório a criar:** `docs/canon/reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md`.
**Origem:** `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §3 bloco 001.8 e §12.1 linha 11 · **P-PILOTO-01** · **D-PILOTO-07** · `PLANO-PILOTOS-AJUSTES-2026-09-08.md` §2.1.
**Depende de:** **EXTRA-001.2** (a trava de turno por conversa, §5 daquela SPEC). Esta SPEC **pendura** nela e não a duplica — §3.3.

---

## 0. Resultado e motivo

> Quatro segurados da Resulta e quatro da AutoFleet falam ao mesmo tempo. Os oito são atendidos. Se o modelo da Resulta ficar lento, se o portal dela travar, ou se um número mandar cinquenta mensagens seguidas, **a AutoFleet não sente nada** — e nenhuma mensagem se perde: o que não cabe agora espera, com o "digitando…" ligado e uma linha dizendo por quê.

📊 **O que os pilotos mediram:** o agente ficou ligado **~1h53 em três dias**, falou com **5 segurados** e **nunca** houve duas corretoras atendendo ao mesmo tempo (DIAGNÓSTICO §0). Ou seja: **o defeito desta SPEC nunca foi observado em produção — ele foi lido no código.** É honesto dizer isso no primeiro parágrafo, porque muda o gate: a prova não pode ser "não aconteceu de novo"; tem de ser **uma corretora travada de propósito, medida contra a outra**.

🔴 **Por que é CRÍTICO mesmo sem incidente:** o Founder registrou o custo em P-PILOTO-01 — *"com centenas de corretoras, um travamento em uma para todas — irreparável para a AutoBrokers"*. Um defeito de isolamento não avisa: ele aparece no primeiro dia em que o produto dá certo.

### 0.1 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | decisão | efeito nesta SPEC |
|---|---|---|
| **D-PILOTO-07** | *"≥ 4 atendimentos simultâneos por corretora e nenhuma corretora interferindo em outra"* | **4 é o piso da COTA**, não o teto do sistema (§6.2). "Nenhuma interferência" vira número medido no BLOCO 0 (§5.4) |
| **D-PILOTO-14** | alta qualidade sem ser exorbitante; AAA opção B; **≤ 12 guardas novos**; bateria sobre motor e acervo real | §12 gasta **10** guardas. Os 2 restantes são para o que o painel achar — ⛔ não para preencher |
| **D-PILOTO-06** | as entregas de 08/09 saíram sem AAA | o semáforo de `buffer_processor.py` nasceu ali e é **alívio, não solução** (texto do próprio Founder em P-PILOTO-01). Esta SPEC termina o trabalho |
| **D-PILOTO-20** | criação de SPEC neste chat; **execução em chat novo** sob AAA opção B | o `PROMPT-DE-ABERTURA-EXTRA-001.8.md` é o que o Founder cola |
| **D-PILOTO-02** | a atendente responder pelo celular pausa o robô — e isso é o desejado | a pausa humana **não** conta contra a cota: conversa pausada não ocupa slot (§6.4) |

### 0.2 EXECUTION CARD — proposto, a confirmar no BLOCO 0

```text
OUTCOME .............. 4+ atendimentos simultâneos POR CORRETORA; uma corretora lenta,
                       travada ou em rajada não muda a latência da outra; zero mensagem perdida
RISCO ................ 8  (ALCANCE 3 o segurado · REVERSIBILIDADE 3 a mensagem sai do prédio ·
                          FREQUÊNCIA 2 todo atendimento)
SUPERFÍCIE ........... 2  (vários comportamentos + peças novas: cota, rodízio, teto, breaker)
PISO APLICADO ........ §3.2 "qualquer coisa que ENVIE" — o caminho alterado é o que responde
                       ao segurado. O piso já daria CRÍTICO sozinho
NÍVEL ................ CRÍTICO — opção B
UNIDADES ............. 7  (A medição · B cota+rodízio · C teto/retry/breaker · D contrapressão ·
                          E processos e líder · F observabilidade · G prova)
COESÃO ............... `buffer_processor.py` é ARQUIVO-HUB (A, B, D, F escrevem nele): UM dono
                       por vez. `llm_factory.py` é o hub de C. F e G são disjuntos do resto
PARALELISMO REAL ..... no máximo 2 escritores: {C llm_factory + graph} ∥ {A/B/D buffer_processor}.
                       E e F entram depois, em série
TIME ................. investigador+pesquisador (1) · desenhista · builder(s) ·
                       3 lentes de ASSUNTO DIFERENTE (dado · código · produto) · red team ·
                       1 juiz fresco de confirmação e auditoria (§6.1 do protocolo)
REFERÊNCIA ........... interna: `backend/app/workers/smith_worker.py:252-278` (a cota por tenant
                       que JÁ existe e funciona) + `backend/tests/test_midia_e_concorrencia_do_webhook.py:519`
                       (a LINHA DE CONTROLE do paralelismo) · externas: §17 E1–E3
GATES ................ G1–G10 da §12, cada um com a mutação que o deixa vermelho
O ELO ................ §0.3
FAIXA DE RELÓGIO ..... 💭 8–12 h
ORÇAMENTO ............ 💭 ≤ 2,5 M tokens de subagentes. Estourou → menos LENTES, nunca menos MUTAÇÃO
```

🔴 **O que é BLOCKER nesta SPEC** (teste do produto, protocolo §2): qualquer achado em que **uma corretora muda o que a outra recebe** — latência, silêncio, mensagem perdida, mensagem duplicada. Isso é isolamento (CLAUDE.md §7) e **não se rebaixa a pendência** (protocolo §6). Tudo o mais — nome de variável, formato de log, tela — é pendência e segue.

### 0.3 🔴 O ELO — onde exatamente uma corretora alcança a outra

A afirmação-título é *"a corretora A atrasa a corretora B **porque** compartilham um recurso sem partição"*. Medi A, medi B, e medi **que B chega em A** — são **quatro** recursos compartilhados, e três deles ninguém tinha apontado:

```
① O SEMÁFORO DE 6 É GLOBAL, E ELE ENVOLVE ATÉ A CONFERÊNCIA BARATA
   buffer_processor.py:76-77   semaforo = asyncio.Semaphore(limite)   # limite=6
   buffer_processor.py:79-83   async with semaforo:  →  await buffer_service.should_process(chave)
   🔴 A conferência de prontidão (um GET no Redis, ~1 ms) está DENTRO do semáforo, atrás de
   até 6 turnos de LLM. Com 4 conversas da Resulta em voo a 10 s cada, a conversa da AutoFleet
   não fica atrás na fila: ela NEM É OLHADA por 10 s. O elo não é "esperar a vez" — é
   "não existir para o varredor".

② A LISTA É UMA SÓ, SEM AGRUPAMENTO E SEM ORDEM
   buffer_processor.py:126-141  redis.scan(match="whatsapp_buffer:*")  → chaves.append(...)
   buffer_processor.py:97       asyncio.gather(*(_uma(c) for c in chaves))
   📊 Zero `sort`, zero agrupamento por corretora, zero rodízio. A ordem é a do SCAN — ordem de
   slot, arbitrária. 50 chaves da Resulta e 1 da AutoFleet: a da AutoFleet cai onde calhar.

③ O RELÓGIO NÃO EXISTE EM LUGAR NENHUM DO TURNO
   📊 grep -n "wait_for\|timeout" backend/app/tasks/buffer_processor.py  →  ZERO linhas
   📊 grep -rn "timeout\|max_retries" backend/app/factories/             →  ZERO linhas
   backend/app/agents/graph.py:1603   result = await graph.ainvoke(initial_state, config)
   backend/app/agents/graph.py:2062   async for event in graph.astream_events(...)
   Uma chamada pendurada segura 1 dos 6 slots até o SDK desistir — e o SDK é quem decide,
   não nós. Quatro pendurados = dois slots para o mundo inteiro.

④ O POÇO DE THREADS É UM SÓ, E NINGUÉM O DIMENSIONOU
   📊 306 `asyncio.to_thread` em 64 arquivos (grep -rn "asyncio.to_thread" backend/app | wc -l),
      24 só no webhook.py
   📊 ZERO `loop.set_default_executor` / `ThreadPoolExecutor` configurado para eles
      (grep -rn "set_default_executor" backend/app  →  0)
   `asyncio.to_thread` usa o executor default do laço: `ThreadPoolExecutor(max_workers=
   min(32, os.cpu_count() + 4))`. Num contêiner de 1 vCPU isso é **5 threads** para TODAS as
   corretoras, TODAS as chamadas ao Supabase e os 24 jobs do agendador. 🔴 Este é o
   recurso que o padrão Bulkhead (§17 E1) manda partir primeiro, e é o único cujo tamanho
   o repositório NÃO SABE — depende do `cpu_count` do contêiner. BLOCO 0 mede.
```

⚠️ **E um quinto elo que NÃO é compartilhamento, e por isso não entra aqui:** o rate limit do webhook é **por IP** (`webhook.py:1387` `@limiter.limit("120/minute")`, `rate_limit.py:28` `key_func=get_real_client_ip`). Todas as corretoras do mesmo provedor dividem o mesmo balde — mas é um balde de **entrada**, e a entrada não é o gargalo medido. Vai para pendência com o número, não para esta SPEC (§18).

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira de todo pacote desta SPEC

### 1.1 Allowlist explícita e privada

| Alias | valor |
|---|---|
| **TESTE-A** | allowlist privada do Founder, por variável de ambiente |
| **TESTE-B** | allowlist privada do Founder, por variável de ambiente |

⛔ **Nunca commitar, imprimir, logar ou publicar os números.** Nas evidências, sempre `TESTE-A`/`TESTE-B`.

🔴 **O que esta SPEC exige e as outras não:** o canário precisa dos **dois números em CORRETORAS DIFERENTES ao mesmo tempo** — é a única forma de provar isolamento. TESTE-A pareado/atendido pela corretora de teste 1, TESTE-B pela corretora de teste 2. Se os dois estiverem na mesma corretora, **o canário não prova nada** e o executor diz isso em vez de declarar verde (§14.1).

### 1.2 O que está autorizado

```
✅ ler todo o repositório · rodar a suíte · rodar scripts read-only
✅ SELECT no banco de produção, só contagens e tempos — NUNCA conteúdo de mensagem
✅ escrever código, testes e documentação · commit e push na branch da SPEC
✅ teste de carga SINTÉTICO, contra o motor, com dublês (§5.3) — sem tocar provedor externo
✅ no canário e só nele: conversas entre TESTE-A e TESTE-B, em corretoras de teste
```

### 1.3 O que permanece proibido

```
⛔ qualquer mensagem a segurado, seguradora, atendente ou grupo real
⛔ usar número operacional da Resulta ou da AutoFleet como remetente
⛔ teste de carga contra a API de LLM, contra a Evolution ou contra portal de seguradora
⛔ ligar o agente numa corretora operacional "só para medir"
⛔ imprimir CPF, CNPJ, telefone, placa, nome de segurado, e-mail ou credencial
⛔ deixar a flag de atraso injetado (§11.2) ligada fora do canário
⛔ merge na `main` sem o gate final da SPEC
```

### 1.4 Verificação imediatamente antes de cada efeito

Ambiente + tenant de teste + conexão fixada + identidade real do remetente + destino normalizado + **a flag de atraso injetado está ligada SÓ para o `company_id` de teste**. Se a identidade não puder ser confirmada: **não enviar**, e não escolher outra conexão automaticamente.

🔴 **A trava própria desta SPEC:** o atraso injetado (§11.2) é o único mecanismo novo capaz de **degradar o produto de propósito**. Ele nasce fail-closed: sem `ISOLAMENTO_ATRASO_ALLOWLIST` preenchida com o `company_id` exato, a função devolve 0 ms e **não dorme**. Lista vazia = ninguém (o mesmo desenho de `JANELA_SILENCIO_EXCECOES`, commit `05f46a9`).

### 1.5 Falta de canal ou ação física do Founder

Continuar código, testes, gates e preparação. Deixar para o Founder só a ação física: parear TESTE-A e TESTE-B em duas corretoras de teste distintas, e criar/dimensionar o serviço no EasyPanel (§15). **Ausência de canário não vira aprovação de produção** — vira status PARCIAL com o nome do que faltou.

---

## 2. Escopo completo e exclusões deliberadas

### 2.1 Obrigatório nesta SPEC

1. **Medir** a latência por etapa do atendimento (webhook → buffer → grafo → LLM → envio) e o tamanho real dos quatro recursos compartilhados do §0.3.
2. **Cota por corretora + rodízio** no processador de buffers, reaproveitando o motor atual; sem fila nova.
3. **Teto por chamada e por turno** no LLM e nas ferramentas; retry com backoff só em erro transitório; **circuit breaker por provedor de LLM**.
4. **Contrapressão**: quando a cota estoura, a mensagem **espera** — nunca se perde, nunca expira em silêncio; "digitando…" ligado; o dono avisado quando a espera passa do combinado.
5. **Processos**: lock de líder em Redis para os 24 jobs do APScheduler, e o caminho preparado (variáveis, comando, ordem) para o Founder separar o serviço de jobs no EasyPanel.
6. **Observabilidade por corretora** na Central de Agentes: em execução, em espera, p95 do turno, motivo da última retenção.
7. **Prova** com duas corretoras de teste, uma travada de propósito, medida contra a outra.

### 2.2 Fora desta SPEC, sem empobrecer o outcome (tabela completa com gatilho de retorno em §18)

Troca de provedor de WhatsApp · multicanal · rate limit por corretora na **entrada** do webhook · executor de threads dedicado por caminho (bulkhead completo) · fila nova em Redis Streams para o atendimento · autoscaling · Prometheus/OpenTelemetry · isolamento no banco (pool por tenant) · breaker de **portal** (é da 001.6, §17 E1 daquela SPEC) · pausa por intervenção humana e trava de turno (são da 001.2).

---

## 3. Autoridades preservadas e arquitetura — o que já existe e por que não se cria nada ao lado

🔴 **CLAUDE.md §5 proíbe criar em paralelo: runtime · scheduler · executor.** Esta SPEC não cria nenhum. Ela **parte** o que já existe.

### 3.1 As peças que são reaproveitadas, por arquivo

| peça | onde já mora | o que esta SPEC faz com ela |
|---|---|---|
| o processador de buffers | `backend/app/tasks/buffer_processor.py:63-110` | **estende**: cota por escopo + rodízio + teto por conversa. Mesma assinatura, parâmetros novos com default |
| a chave com tenant dentro | `backend/app/services/message_buffer_service.py:36-57` (`whatsapp_buffer:{escopo}:{telefone}`) | **lê** o escopo da chave. O isolamento já está na chave desde a SPEC-063 Bloco H; faltava alguém usá-lo para escalonar |
| **a cota por tenant** | `backend/app/workers/smith_worker.py:41` (`WORK_TENANT_CONCURRENCY`), `:58` (`self._por_tenant`), `:263-278` (`_agendar`/`_liberar_slot`) | **copia a forma, não o código**: é o mesmo desenho (dicionário por `company_id`, teto, liberação no `done_callback`), já em produção para Work Runs. É a REFERÊNCIA INTERNA do card |
| a fila durável com consumer group | `backend/app/services/work/queue.py:26-28, :78-79, :100, :116` (Streams, `xreadgroup`, `xautoclaim`, `xack`) | **lê e REJEITA** para o atendimento — §6.1 explica por quê. Não se cria fila nova nem se migra a existente |
| o lock com `company_id` na chave | `backend/portal_worker/leases.py:286` (`{prefixo}:{empresa}:{portal}:{conta}`), `:421` (`set(nx=True, ex=...)`), `:130-145` (Lua de renovar/liberar) | **copia o padrão** para o lock de líder do agendador (§9.2). ⛔ Nunca `DEL` cego |
| o espaçamento por corretora | `backend/app/services/platform_outbound.py:119` (`platform_gate:{company_id}`), `:582-584` | **precedente**: já existe chave Redis com tenant no caminho de envio. Esta SPEC segue a mesma convenção de nome |
| a fábrica de LLM | `backend/app/factories/llm_factory.py:140-253` | **recebe** `timeout` e `max_retries` nos quatro construtores. Nenhuma fábrica nova |
| a Central de Agentes | `backend/app/core/central_de_agentes.py` (cache Redis 60 s; *"zero migration, zero tabela nova"*), `backend/app/api/admin_spec034.py:56-67`, frontend `app/admin/central-agentes/page.tsx:640` | **ganha um bloco por corretora**. Zero tabela nova, como o próprio módulo declara |
| a trava de turno por conversa | **EXTRA-001.2 §5** (`abrir_turno`/`fechar_turno`, chave `whatsapp_turno:{escopo}:{telefone}`) | **pendura**: a cota entra ANTES da trava, e a trava continua sendo por conversa (§3.3) |

### 3.2 O contrato lógico, sem tabela nova

```text
SCAN whatsapp_buffer:*                     (o que já existe)
  → MGET em lote: quais estão prontas       (§5.2 — a conferência sai de dentro do semáforo)
  → agrupar por ESCOPO e intercalar          (§6.2 — o rodízio)
  → cota[escopo]  →  teto global             (§6.3 — nesta ordem, e a ordem é a regra)
  → trava de turno da 001.2                  (por conversa, não por corretora)
  → get_and_clear (GET+DEL atômico, já existe)
  → processar COM TETO DE TEMPO              (§7.2)
  → registrar o turno em messages.payload.turn (§5.1 — o mesmo vocabulário do chat)
```

Supabase continua a verdade durável; Redis continua trânsito, lease e cache (CLAUDE.md §6). **Nenhuma fila nova, nenhum publisher novo, nenhum scheduler novo.**

### 3.3 Onde esta SPEC encosta na 001.2, e onde ela para

A 001.2 §5.4 diz, com todas as letras: *"⛔ Trava por corretora é o defeito da EXTRA-001.8, não o conserto desta SPEC"*, e nomeia `backend/tests/test_midia_e_concorrencia_do_webhook.py:519` como **linha de controle** — o teste que prova que conversas diferentes continuam em paralelo.

```
001.2 entrega:  UMA resposta por rajada           → trava por (escopo, telefone)
001.8 entrega:  NENHUMA corretora trava a outra   → cota por escopo + rodízio + teto
```

🔴 **As duas travas convivem e a ordem importa:** a cota é adquirida **antes** da trava de turno. Se fosse depois, uma conversa esperando a trava (porque outra rodada da mesma conversa está em voo) ocuparia um slot de cota da corretora — e a 001.2 teria criado, dentro da 001.8, o gargalo que a 001.8 existe para matar.

⚠️ **Se a 001.2 ainda não estiver na `main` quando esta SPEC começar:** o BLOCO 0 mede (`grep -n "abrir_turno" backend/app/services/message_buffer_service.py`), e o executor implementa a cota deixando o ponto de inserção da trava **escrito e vazio**, com a ordem documentada. ⛔ Não implementar a trava aqui: seria motor paralelo.

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código de produto

> **Este documento envelhece. O número do executor vence** (protocolo §5 ①).

| # | premissa desta proposta | comando que a confere | valor de 13/09 |
|---|---|---|---|
| 1 | o semáforo é global e vale 6 | `sed -n '60,80p' backend/app/tasks/buffer_processor.py` | `_PARALELISMO_PADRAO = 6`, `Semaphore(limite)` na linha 77 |
| 2 | a conferência está dentro do semáforo | `sed -n '79,85p' backend/app/tasks/buffer_processor.py` | `async with semaforo:` → `should_process` na linha 81 |
| 3 | zero timeout no processador | `grep -n "wait_for\|timeout" backend/app/tasks/buffer_processor.py` | **0 linhas** |
| 4 | zero timeout/retry na fábrica de LLM | `grep -rn "timeout\|max_retries" backend/app/factories/` | **0 linhas** |
| 5 | o turno não tem teto | `grep -n "ainvoke\|astream_events" backend/app/agents/graph.py` | `:1603`, `:2062` — sem `wait_for` |
| 6 | 24 jobs, um processo, sem lock de líder | `grep -c "add_job" backend/app/tasks/buffer_processor.py` · `grep -rn "advisory\|leader\|lider" backend/app \| wc -l` | **24** · **0** |
| 7 | uvicorn sem `--workers` | `grep -n CMD backend/Dockerfile` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 8 | 306 `to_thread` sem executor dimensionado | `grep -rn "asyncio.to_thread" backend/app \| wc -l` · `grep -rn "set_default_executor" backend/app` | **306** · **0** |
| 9 | 🔴 **quantas threads o contêiner realmente tem** | `python -c "import os,concurrent.futures as f; print(os.cpu_count(), min(32,(os.cpu_count() or 1)+4))"` **rodado DENTRO do smith-api implantado** | ⛔ **DESCONHECIDO** — é o número mais importante do BLOCO 0 |
| 10 | a cota por tenant já existe para Work Runs | `sed -n '252,280p' backend/app/workers/smith_worker.py` | `CONCORRENCIA_POR_TENANT`, `_por_tenant`, `_liberar_slot` |
| 11 | Streams+consumer group já existem | `sed -n '26,30p;74,120p' backend/app/services/work/queue.py` | `STREAM_KEY`, `CONSUMER_GROUP`, `xreadgroup`, `xautoclaim`, `xack` |
| 12 | o lease com tenant na chave já existe | `sed -n '86,96p;280,290p;415,425p' backend/portal_worker/leases.py` | TTL 120 s, `set(nx=True, ex=...)`, chave com `empresa` |
| 13 | TTL do buffer = 60 s e teto de espera = 25 s | `sed -n '73,76p' backend/app/core/config.py` | `BUFFER_DEBOUNCE=8 · MAX_WAIT=25 · TTL=60` |
| 14 | a trava de turno da 001.2 já está na árvore? | `grep -n "abrir_turno" backend/app/services/message_buffer_service.py` | **a confirmar** — muda §3.3 |
| 15 | latência real por etapa hoje | §5.1 — a consulta ao acervo | ⛔ **não existe registro no caminho do atendimento** |
| 16 | quantas corretoras com agente ligado hoje | `select count(*) from agents where agent_role='attendance' and is_active` | 📊 a remedir (08/09: **3 de 3 desligados**) |

**GATE B0.** A matriz acima preenchida com o valor de hoje e o comando ao lado; o item **9** medido no serviço implantado, não na máquina do executor; o item **15** com a decisão registrada de qual sinal existente se usa (§5.1). 🔴 **Item 9 ausente = o BLOCO E não pode ser dimensionado, e a SPEC diz isso em vez de chutar.**

**MUTAÇÃO B0.** O desenhista afirma no aquecimento, assinado, que *"o semáforo de 6 já é por corretora, porque a chave do buffer tem o escopo"*. O executor tem de refutar com a linha 77 e explicar que a chave isola **dados**, não **vez na fila**.

---

## 5. BLOCO A — a medição, antes de qualquer conserto

### 5.1 O relógio do atendimento passa a existir — com o vocabulário que já existe

📊 **Achado que reordena o bloco:** o turno **é** registrado, mas só no chat do painel. `backend/app/api/chat.py:1206-1223` monta `payload.turn` com `ttft_ms`, `total_ms`, `stages[]`, `attempt`, `status`, e (de `:1162-1167`) `finish_reason`, `usage`, `continuations`, `truncated`; gravado em `messages.payload` por `chat.py:938-958`. 🔴 **O caminho do atendimento (`webhook.process_whatsapp_message_background`) não grava nada disso.** Sem isso, "latência por etapa" não é medível e o gate da §11 não tem régua.

**Contrato — mesmo nome, mesmo lugar, zero tabela nova:**

```python
# backend/app/api/webhook.py, na mensagem do AGENTE que já é gravada
payload["turn"] = {
    "status": "completed" | "failed" | "timeout" | "adiado",
    "total_ms": int,                  # do primeiro evento do webhook ao envio aceito
    "etapas": [                       # ⚠️ nome em português como o resto do módulo;
        {"nome": "buffer_espera",  "ms": int},   # last_at → saída do rodízio
        {"nome": "fila_cota",      "ms": int},   # espera pela cota da corretora
        {"nome": "grafo",          "ms": int},   # ainvoke inteiro
        {"nome": "envio",          "ms": int},   # whatsapp_service.send_message
    ],
    "provedor": str, "modelo": str,   # para o breaker do §7.3 ter a quem culpar
    "finish_reason": str | None, "usage": dict | None,   # os MESMOS nomes do chat.py
}
```

⛔ **Não criar um segundo vocabulário.** Se `chat.py` chama `total_ms`, o atendimento chama `total_ms`. Dois nomes para o mesmo fato é o defeito que CLAUDE.md §12.1 manda consertar no campo, não no texto.

O tenant chega por `conversations.company_id` (já escrito), como no chat. 📊 `platform_sends(company_id, phone, kind, sent_at)` — migration `backend/supabase/migrations/20260720_02_spec045_platform_sends.sql:7-20`, índice `(company_id, phone, sent_at desc)` — continua sendo a contagem de **vazão de saída**, e não muda.

### 5.2 A conferência de prontidão sai de dentro do semáforo — e vira um só ida-e-volta

```python
# message_buffer_service.py — a regra continua UMA, e o lote a chama
def _esta_pronta(data: dict, agora: datetime) -> bool:
    """A regra de debounce, extraída de `should_process` SEM mudar o comportamento:
    8 s desde a última OU 25 s desde a primeira (pisos travados, `:158`/`:166`)."""

async def should_process(self, key: str) -> bool:
    """Fica. Continua o caminho de uma chave só (a 001.2 o chama)."""
    ...  # passa a delegar a `_esta_pronta`

async def prontas(self, chaves: list[str]) -> list[str]:
    """UM `MGET` para o lote inteiro; devolve as chaves prontas, na ordem recebida.
    ⛔ NÃO consome o buffer: `get_and_clear` continua sendo o único consumidor, e
    continua sendo GET+DEL atômico (`:183-186`). Aqui só se PERGUNTA."""
```

🔴 **Por que isto é do bloco de medição e não do de fila:** hoje cada varredura faz **um GET por conversa aberta, por segundo, atrás de um semáforo de 6**. Isso é ao mesmo tempo o custo que ninguém contou e a causa do elo ① — e não dá para medir a fila de uma corretora enquanto a conferência da outra está presa atrás de um turno de LLM.

### 5.3 O teste de carga, sintético e reproduzível

```
backend/tests/test_uma_corretora_nao_trava_a_outra.py
```

Exercita `processar_buffers_prontos` — **o motor**, com dublês, como o teste que já existe faz (`test_midia_e_concorrencia_do_webhook.py:61-89` carrega o módulo por AST). Cenário:

```
corretora DOENTE   50 chaves, processador que dorme 10 s      (a rajada + o LLM lento)
corretora SADIA     4 chaves, processador que dorme 0,2 s
medir              tempo até a última chave SADIA ser processada
CONTROLE           a mesma rodada SEM a corretora doente      ← é ela que dá direito à conclusão
```

⚠️ **A linha de controle é obrigatória (CLAUDE.md §9.2):** sem a rodada sem a doente, um ambiente rápido "passaria" por acaso e o mérito iria para o lugar errado.

⛔ **Sem tenant de teste seguro no banco, este bloco não para.** O teste de carga é 100% sintético (dublês de buffer e de processador, zero Redis real, zero LLM, zero envio) e roda em qualquer máquina. O que **exige** tenant real é só o canário da §14 — e esse é 🧑 do Founder.

### 5.4 🔴 O X do gate sai daqui, e não de palpite

📊 **`grep -c -i "p95" docs/canon/PENDENCIAS.md` → 0.** O projeto **não tem SLO declarado** — o protocolo §7.1 já diz isso ("⛔ o que NÃO temos, declarado: … alvo de latência (SLO)"). D-PILOTO-07 pede "nenhuma interferência" e não dá número.

**Contrato do X:** o BLOCO 0 mede a mediana e o p95 do `total_ms` da corretora SADIA **sozinha** (§5.3, rodada de controle). O gate da §11 exige:

```
p95 da SADIA com a DOENTE presente   ≤   p95 da SADIA sozinha  +  X
X = 💭 2 s de partida, SUBSTITUÍDO pelo número medido no BLOCO 0 (proposta: p95 sozinha × 0,25)
```

🔴 **O X vai escrito no EXECUTION CARD do relatório, com o comando que o produziu.** Número sem comando, em documento novo, é defeito de revisão (CLAUDE.md §12.1).

**GATE A.** ① o turno do atendimento aparece em `messages.payload.turn` com `total_ms` e as 4 etapas, no canário; ② `prontas()` devolve exatamente o mesmo conjunto que `should_process` uma a uma, sobre 20 buffers do corpus; ③ o teste de carga roda e imprime os dois p95 e a linha de controle.
**MUTAÇÃO A.** `prontas()` passa a usar uma régua própria (`>= 5 s`) em vez de `_esta_pronta` → o teste de equivalência ② fica **vermelho**. É assim que se prova que a regra continua sendo UMA.

---

## 6. BLOCO B — a cota por corretora e o rodízio

### 6.1 A decisão, com nota — e por que fila nova é a resposta errada

| opção | nota | por quê |
|---|---|---|
| **um pool com COTA por corretora + RODÍZIO, dentro do processador atual** | **91** | reaproveita o motor (CLAUDE.md §5), preserva o teto global (o event loop e o poço de threads continuam finitos), garante o piso de 4 da D-PILOTO-07 **e** garante que a vez chega. É a forma que o `SmithWorker` já usa em produção e que a k8s APF (§17 E2) implementa em escala |
| um pool POR corretora (semáforo dedicado, sem teto global) | 62 | dá isolamento e tira o teto: N corretoras × 4 estoura o event loop e o poço de threads do §0.3 ④. Bulkhead sem admissão é trocar "uma trava todas" por "todas travam juntas" |
| **fila nova em Redis Streams por corretora** | **45** | ⛔ **motor paralelo.** O buffer no Redis **já é a fila**, e o `GET+DEL` em pipeline (`message_buffer_service.py:183-186`) **já é** a entrega exatamente-uma-vez. 📊 Streams com consumer group já existem no repo (`work/queue.py:26-116`) e servem Work Runs — duplicá-los para o WhatsApp criaria duas verdades sobre a mesma mensagem |
| aumentar `WHATSAPP_BUFFER_PARALELISMO` de 6 para 24 | 30 | mais slots para a corretora que já monopoliza. Não é isolamento; é o mesmo defeito, mais caro |

🔴 **E a lição que o próprio repositório já pagou:** `smith_worker.py:264-266` recusa a mensagem quando o tenant está no teto e **não dá `ack`** — a entrada fica pendurada no PEL do consumidor e só volta pelo `xautoclaim` depois do tempo de ocioso. Com um worker só, a corretora no teto fica esperando por tempo de relógio, não por vaga. **A nossa cota não pode herdar isso**, e não herda: o buffer **fica no Redis** e a varredura de 1 s o reencontra (§8.1).

### 6.2 O contrato

```python
# backend/app/services/message_buffer_service.py
@staticmethod
def escopo_da_chave(chave: str) -> str:
    """`whatsapp_buffer:{escopo}:{telefone}` → escopo.
    🔴 Chave malformada, ou escopo vazio/`sem-integracao` → devolve "" (fail-closed).
    A recusa de escopo vazio é a mesma da 001.2 §5.3 e pela mesma razão: duas corretoras
    com o mesmo telefone cairiam na mesma chave, e uma trava a outra."""

# backend/app/tasks/buffer_processor.py
_COTA_PADRAO = 4                 # 🔴 D-PILOTO-07: o PISO é 4 por corretora
_PARALELISMO_PADRAO = 6          # fica o nome; o VALOR sobe (§9.3)

def ordenar_em_rodizio(chaves: list[str]) -> list[str]:
    """Agrupa por escopo e intercala: A1 B1 C1 · A2 B2 C2 · A3 …
    Determinística: dentro do escopo preserva a ordem recebida; entre escopos, ordem
    estável do escopo. ⛔ Não é aleatório e não é por tamanho de fila — é rodízio simples.
    Sem determinismo o guarda G2 não consegue afirmar nada."""

async def processar_buffers_prontos(chaves, buffer_service, processar,
                                    paralelismo: int = 0,
                                    cota_por_corretora: int = 0,
                                    timeout_s: float = 0) -> dict:
    """Parâmetros novos, todos com default 0 = "leia do ambiente".
    ⚠️ A assinatura antiga continua válida: `test_midia_e_concorrencia_do_webhook.py:519`
    chama com `paralelismo=6` e `paralelismo=1` e TEM DE CONTINUAR VERDE (§3.3)."""
```

Variáveis de ambiente, por nome: **`WHATSAPP_COTA_POR_CORRETORA`** (💭 4) · **`WHATSAPP_BUFFER_PARALELISMO`** (já existe) · **`WHATSAPP_TURNO_TIMEOUT_S`** (§7.2).

### 6.3 A ordem de aquisição É a regra

```python
async def _uma(chave: str) -> bool:
    escopo = buffer_service.escopo_da_chave(chave)
    if not escopo:
        return _adiar(chave, motivo="sem_escopo")        # fail-closed, uma linha no feed
    async with cota_de(escopo):            # ① a COTA DA CORRETORA primeiro
        async with semaforo_global:        # ② o teto do processo depois
            token = await buffer_service.abrir_turno(escopo, phone)   # ③ 001.2, por conversa
            if token is None:
                return False               # o buffer FICA; a varredura de 1 s tenta de novo
            try:
                buffer = await buffer_service.get_and_clear_buffer(chave)
                ...
                await asyncio.wait_for(processar(...), timeout=teto)   # §7.2
            finally:
                await buffer_service.fechar_turno(escopo, phone, token)
```

🔴 **Cota antes do teto global, sempre, e nunca o contrário.** Se o teto global viesse primeiro, uma conversa esperando a cota da própria corretora estaria **segurando um slot global** — a corretora saturada passaria a consumir os 6 slots do processo só para esperar. É a inversão que transforma a proteção no defeito.

🔴 **E os semáforos por escopo são criados sob demanda e removidos quando zeram** — o mesmo `_liberar_slot` do `smith_worker.py:272-278`. Um dicionário que só cresce é um vazamento de memória com o nome de isolamento.

### 6.4 O que NÃO ocupa cota

Conversa **pausada por intervenção humana** (D-PILOTO-02) e conversa dentro da **janela de silêncio** não chegam a `processar` — mas hoje chegam a ocupar um slot porque o silêncio é decidido lá dentro. ⚠️ **Esta SPEC não move a decisão de silêncio** (é da 001.2/001.3). O que ela faz é medir: se o `total_ms` de uma conversa calada for < 50 ms, ela sai da cota na prática. Se não for, vira **pendência com o número**, não conserto silencioso.

**GATE B.** ① 50 chaves de uma corretora + 4 de outra pelo motor real: as 4 terminam dentro de X (§5.4); ② `ordenar_em_rodizio` sobre 3 corretoras devolve intercalado e **estável entre execuções**; ③ `escopo_da_chave("whatsapp_buffer:sem-integracao:5511...")` → `""`, e a chave é adiada, não processada; ④ **o teste de paralelismo existente continua verde** (a linha de controle da 001.2).
**MUTAÇÃO B.** (a) remover a cota (`cota_por_corretora=10_000`) → o gate ① fica **vermelho**; (b) inverter a ordem (global antes da cota) → o gate ① fica **vermelho**; (c) trocar o rodízio pela ordem do SCAN → o gate ② fica **vermelho**.

---

## 7. BLOCO C — o relógio do modelo e das ferramentas

### 7.1 Teto por chamada, na fábrica

```python
# backend/app/factories/llm_factory.py — nos QUATRO construtores (:164, :200, :219, :230)
LLM_TIMEOUT_S   = int(os.getenv("LLM_TIMEOUT_SEGUNDOS", "0"))   # 0 = medido no BLOCO 0
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
```

📊 Hoje a fábrica passa só `model`, `max_tokens`, `api_key`, `callbacks`, `streaming`, `temperature` — **zero** `timeout`, **zero** `max_retries` (grep no diretório: 0 linhas). O SDK aplica o default dele, que nós não escolhemos e não medimos.

⚠️ **O valor do teto não se inventa.** O BLOCO 0 mede o p95 do `total_ms` do chat (que **já** grava, `chat.py:1210`) e o teto nasce em **p95 × 3**, com piso de 60 s. 💭 Partida: 90 s. O número final vai no card com o comando.

### 7.2 Teto por TURNO, e a distinção que evita cortar quem está trabalhando

```
ATENDIMENTO (webhook, sem streaming ao segurado)
   asyncio.wait_for(processar(...), timeout=WHATSAPP_TURNO_TIMEOUT_S)   💭 120 s de partida
   estourou → status "timeout" no payload.turn · a mensagem NÃO se perde (§8) ·
              o dono é avisado · ⛔ nunca um "não entendi" ao segurado

CHAT DO PAINEL (SSE, com streaming)
   ⛔ NÃO se põe `wait_for` em volta do `astream_events` (graph.py:2062).
   Um turno que está EMITINDO delta não está travado — cortá-lo é regressão da SPEC-096,
   que entregou exatamente esse streaming. O relógio certo é o TEMPO SEM PROGRESSO:
   nenhum delta por N s → encerra o turno com `status="timeout"`.
   O heartbeat de 15 s (chat.py:398) fica: ele é para o proxy, não é teto de turno.
```

🔴 **Esta distinção é o coração do bloco.** Um teto total corta a resposta longa e boa; um teto de silêncio corta só o que está morto.

### 7.3 Retry com backoff — e só no que é transitório

```python
TRANSITÓRIO  → tenta de novo:  timeout · erro de conexão · HTTP 429 · HTTP 5xx
⛔ NUNCA      → falha na hora:  400 · 401 · 403 · 404 · chave inválida · modelo inexistente
backoff: full jitter — espera = random(0, base·2ⁿ), base 2 s, teto 30 s, no máximo 2 voltas
```

⚠️ **Repetir um 401 queima a cota da corretora e atrasa todo mundo** — é o mesmo raciocínio que a 001.6 §B3.2 escreveu para credencial de portal recusada. **Mesmo princípio, assunto diferente, código diferente. Não se reaproveita função; reaproveita-se a lição.**

### 7.4 Circuit breaker POR PROVEDOR — e por que não é por corretora

```
chave Redis:  llm_breaker:{provedor}        (openai · anthropic · google · openrouter)
estados:      fechado → aberto → meio-aberto      (§17 E1)
abre:         N falhas não-transitórias seguidas, ou N timeouts numa janela (💭 5 em 60 s)
meio-aberto:  depois de T (💭 120 s), deixa passar UMA chamada
```

🔴 **Por provedor, não por corretora, e a razão é o isolamento:** a Anthropic cair é um fato do mundo, não da Resulta. Um breaker por corretora abriria N vezes para o mesmo fato e cada corretora pagaria N timeouts para descobrir sozinha o que a primeira já sabia.

⛔ **Não duplicar o breaker de PORTAIS da EXTRA-001.6 §B3.3.** Aquele é por conta de portal (`portal_accounts.health`), tem o *"half-open é o gesto humano"* (salvar a senha nova) e vive no `portal-worker`. Este é por provedor de LLM, vive no `smith-api` e volta por timer. **Se a 001.6 tiver deixado um helper genérico de breaker, o executor o REUSA e diz onde**; se não tiver, escreve o mínimo aqui e registra a consolidação como pendência.

🔴 **Breaker aberto não vira silêncio.** Aberto → a mensagem é **retida** (§8), o dono é avisado com frase humana 💭 *"o provedor de inteligência está fora do ar há 3 minutos; as conversas estão guardadas e vão ser respondidas assim que voltar"*, e **nada** é enviado ao segurado. Um breaker que faz o agente calar sem avisar é pior que timeout.

### 7.5 As ferramentas também

📊 O que **já tem** teto: InfoCap 8–15 s (`infocap_connector.py:175, :1459, :1460, :4416`), Evolution 20–30 s (`evolution_go.py:346, :443, :454`), visão 30 s (`attendance_media.py:32`), subagente 30 s (`subagent_tool.py:36`). O que **não tem**: 4 clientes `httpx.AsyncClient()` sem timeout algum (`mcp_servers/base_server.py:75`, `mcp_servers/google_drive_server.py:208`, `mcp_oauth_service.py:251` e `:384`) e as chamadas ao Supabase.

**Contrato:** um teto default para todo `httpx.AsyncClient` criado no backend, e um guarda que **conta zero** clientes sem `timeout` (G6). ⚠️ Os 4 achados acima estão fora do caminho do atendimento — entram porque são 4 linhas e porque o guarda só consegue ficar vermelho se a regra valer para todos.

**GATE C.** ① os 4 construtores da fábrica recebem `timeout` e `max_retries` (teste que lê os kwargs reais, não o código-fonte); ② `wait_for` no caminho do atendimento, e **nenhum** `wait_for` total em volta do `astream_events`; ③ backoff com jitter: duas chamadas com o mesmo `n` dão valores diferentes; ④ 401 não entra no backoff; ⑤ breaker abre com 5 falhas e a 6ª chamada não sai; ⑥ zero `httpx.AsyncClient()` sem timeout.
**MUTAÇÃO C.** (a) tirar `timeout` de um construtor → ① vermelho; (b) aplicar backoff ao 401 → ④ vermelho; (c) breaker sem estado meio-aberto (nunca fecha) → uma sexta chamada depois de T falha → ⑤ vermelho.

---

## 8. BLOCO D — contrapressão: a mensagem espera, nunca se perde

### 8.1 🔴 O defeito que a contrapressão descobre: o buffer EXPIRA

```
message_buffer_service.py:127   await self.redis.setex(key, settings.BUFFER_TTL_SECONDS, ...)
core/config.py:75               BUFFER_TTL_SECONDS: int = 60
```

📊 **O TTL do buffer é 60 s, contado desde a ÚLTIMA escrita.** Enquanto a fila anda em 1 s isso é uma rede de segurança. Com a cota cheia e 50 conversas na frente, **uma conversa pode esperar mais de 60 s — e o Redis apaga o buffer.** O segurado escreveu, o webhook respondeu `{"status":"buffered"}`, e a mensagem sumiu **sem uma linha em lugar nenhum**. Isto não é consequência da cota: já é verdade hoje, e a cota o torna alcançável.

**Contrato:**

```python
async def adiar(self, chave: str, *, motivo: str) -> None:
    """Renova o TTL do buffer (EXPIRE) e incrementa o contador de espera do escopo.
    ⛔ NÃO reescreve o conteúdo (não mexe em `last_at`: isso remataria o debounce e a
    rajada nunca fecharia). Só o relógio de VIDA da chave, nunca o de PRONTIDÃO."""
```

Chamado sempre que uma chave pronta **não** é servida: cota cheia · turno tomado (001.2) · breaker aberto · escopo vazio. `motivo` é uma das quatro palavras e vai para o contador e para o feed.

### 8.2 A conta que fecha — entrada = saída + retidas

O resumo de cada varredura deixa de ser `{processadas, falhas, vistas}` e passa a ser:

```python
{"vistas": int, "prontas": int, "processadas": int,
 "adiadas": {"cota": int, "turno": int, "breaker": int, "sem_escopo": int},
 "falhas": int, "timeouts": int, "expiradas": int}
```

🔴 **`expiradas` tem de ser ZERO, e o guarda G7 o afirma.** É o único número desta SPEC que não admite "quase". Uma chave que estava pronta numa varredura e não existe na seguinte, sem ter sido processada, é uma mensagem de segurado perdida.

### 8.3 O "digitando…" e o aviso ao dono

- **Presença "digitando…"**: o contrato é da **EXTRA-001.2 §6.4** (`sendPresence`, `presence ∈ {composing, paused, …}`). ⛔ **Não reimplementar.** Esta SPEC só acrescenta o gatilho: conversa **adiada por cota** liga a presença, para o segurado ver que foi lido. Se a 001.2 não estiver na `main`, o gatilho fica escrito e desligado, e vira pendência nominal.
- **Aviso ao dono**: uma corretora acima da cota por mais de N s (💭 60) gera **um** aviso ao destino de suporte dela — pelo caminho que a **EXTRA-001.3** governa, com a mesma guarda de "humano já está nesta conversa" e **um** aviso por janela, nunca de 10 em 10 minutos (foi assim que o grupo virou ruído, DIAGNÓSTICO §1.5). ⛔ Nenhum destino novo, nenhum canal novo.
- 💭 Copy do aviso (ilustrativa, nunca citável): *"estamos com 12 conversas ao mesmo tempo aqui na Resulta e 4 estão esperando a vez. Ninguém foi perdido — vão sendo respondidas por ordem de chegada."*

**GATE D.** ① 200 chaves de uma corretora, cota 4, processador de 2 s: **zero** `expiradas` e entrada = processadas + adiadas; ② `adiar` renova o TTL e **não** altera `last_at` (duas leituras do JSON antes e depois); ③ o aviso ao dono sai **uma vez** por janela, não por varredura.
**MUTAÇÃO D.** (a) `adiar` vira `pass` → ① fica **vermelho** com `expiradas > 0`; (b) `adiar` reescrever o buffer inteiro → ② fica **vermelho** (a rajada nunca fecha); (c) tirar a janela do aviso → ③ fica **vermelho** com N avisos.

---

## 9. BLOCO E — processos, réplicas e o lock de líder

### 9.1 A verdade desconfortável primeiro

🔴 **Mais processos aumentam o TETO. Cota e rodízio produzem o ISOLAMENTO.** O que a D-PILOTO-07 pede é isolamento — e os blocos B, C e D o entregam **num processo só**. Este bloco existe para duas coisas diferentes: (a) impedir que uma réplica acidental **duplique** os 24 jobs, e (b) deixar o caminho pronto e nomeado para o Founder subir capacidade quando quiser.

| opção | nota | por quê |
|---|---|---|
| **lock de líder + `SCHEDULER_ENABLED`, mantendo 1 processo** | **88** | fecha o risco real (réplica dupla avisando duas vezes o mesmo grupo), custa zero mudança de deploy, e é **pré-requisito** das outras duas. Entra nesta SPEC |
| serviço `smith-jobs` separado (mesma imagem, comando próprio), API com o agendador desligado | 84 | é o alvo certo e tem precedente no repo (o `portal-worker` já é assim). Mas depende de 🧑 criar o serviço no EasyPanel. Fica **preparado e desligado** nesta SPEC |
| `uvicorn --workers N` | 41 | multiplica o servidor web e **quebra** o que é memória de processo: 📊 P-096-STOP-MULTIPROCESSO (`PENDENCIAS.md:10255`) diz que `TURNOS_ATIVOS` vive na memória e o `POST /chat/stop` cairia noutro worker → 404. Não entra sem consertar aquilo |

### 9.2 O lock de líder — no padrão que o repositório já usa

```python
# backend/app/tasks/buffer_processor.py, antes de scheduler.start()
CHAVE  = "autobrokers:scheduler:lider"
TTL_S  = 60              # renovado a cada 20 s por uma task
token  = uuid4().hex     # E3: "set a non-guessable large random string"

SET autobrokers:scheduler:lider {token} NX EX 60      # ganhou → é o líder
EVAL <script oficial da doc>  → renova/solta só se o valor ainda for o token
```

O script de soltura é o **literal da documentação do Redis** (§17 E3) — o mesmo que `portal_worker/leases.py:130-145` já usa. ⛔ **Nunca `DEL` cego.**

```
não é líder  →  NÃO inicia o agendador; `/health` diz `scheduler: "seguidor"`
perdeu o lock (renovação falhou)  →  PARA o agendador e volta a tentar adquirir
Redis fora   →  🔴 FAIL-CLOSED para os jobs que ENVIAM (watchdogs, follow-up, cobrança);
                fail-open só para os que apenas leem/higienizam. A lista de quais é qual
                vai na SPEC, job a job, e o guarda G8 a verifica.
```

⚠️ **Fail-closed aqui é o oposto do que `minio_backup.py:295-297` faz hoje** (segue sem Redis). Está certo lá — backup duplicado não machuca ninguém. Está errado para o `handoff_watchdog`: dois avisos ao mesmo grupo é exatamente o ruído que a 001.3 existe para matar.

### 9.3 O poço de threads deixa de ser implícito

```python
# backend/app/main.py, no lifespan, ANTES de start_buffer_scheduler()
loop.set_default_executor(ThreadPoolExecutor(
    max_workers=int(os.getenv("EXECUTOR_THREADS", "0")) or (min(32, (os.cpu_count() or 1) + 4)),
    thread_name_prefix="to_thread"))
```

🔴 **O default de hoje depende do `cpu_count` do contêiner e ninguém o conhece** (BLOCO 0 item 9). Num contêiner de 1 vCPU são **5 threads** para 306 pontos de `to_thread` — e é por elas que passam quase todas as leituras ao Supabase de **todas** as corretoras. Tornar o número explícito e nomeado (`EXECUTOR_THREADS`) é o mínimo; é literalmente o que o padrão Bulkhead manda (§17 E1: *"consider using processes, thread pools, and semaphores"*).

⚠️ **Um executor por caminho (bulkhead completo) fica FORA** — mudaria 306 chamadas. Vai para §18 com o gatilho: quando o BLOCO 0 mostrar saturação do poço sob a carga do §5.3.

### 9.4 O que o Founder muda no EasyPanel

| serviço | o que muda | quando |
|---|---|---|
| **smith-api** | variáveis novas: `WHATSAPP_COTA_POR_CORRETORA`, `WHATSAPP_TURNO_TIMEOUT_S`, `LLM_TIMEOUT_SEGUNDOS`, `LLM_MAX_RETRIES`, `LLM_BREAKER_FALHAS`, `LLM_BREAKER_SEGUNDOS`, `EXECUTOR_THREADS`, `SCHEDULER_ENABLED`, `ISOLAMENTO_ATRASO_ALLOWLIST` (vazia em produção) | nesta SPEC |
| **smith-api** | réplicas: continua **1** | nesta SPEC |
| **smith-jobs** (novo, opcional) | mesma imagem; comando `python -m app.tasks.jobs_runner`; `SCHEDULER_ENABLED=true`; 1 réplica. A API passa a `SCHEDULER_ENABLED=false` | 🧑 quando o Founder quiser, **depois** desta SPEC |
| **portal-worker** | nada | — |

⛔ **Nenhum valor de variável nesta proposta, nem no relatório. Só o NOME.**

**GATE E.** ① dois processos do mesmo código: **um só** inicia o agendador, e o outro diz `seguidor` no `/health`; ② matar o líder → o seguidor assume em ≤ TTL; ③ Redis fora → nenhum job de envio roda; ④ `EXECUTOR_THREADS` é lido e o executor default tem o tamanho pedido.
**MUTAÇÃO E.** (a) soltar o lock com `DEL` cego → um teste com dois donos fica **vermelho**; (b) fail-open para o `handoff_watchdog` → ③ fica **vermelho**.

---

## 10. BLOCO F — a Central de Agentes passa a ver por corretora

📊 Hoje a Central responde *"o agente X produziu?"*, nunca *"a corretora Y foi atendida em quanto tempo?"*: `backend/app/core/central_de_agentes.py` calcula 5 estados por **grupo de agentes** (🟢 SAUDAVEL · 🟡 PULSA_SEM_PRODUZIR · ⚪ DESLIGADO · 🔴 PARADO · ⚫ NAO_MEDIDO), com cache Redis de 60 s, e o módulo declara na linha 29: *"⛔ Zero migration, zero tabela nova"*. **Esta SPEC respeita a declaração.**

**Contrato — um bloco novo no MESMO JSON de `GET /api/admin/spec034/agents-status`:**

```json
"atendimento_por_corretora": [
  {"company_id": "…", "nome": "…",
   "em_execucao": 2, "em_espera": 5, "cota": 4,
   "p95_ms_24h": 9400, "mediana_ms_24h": 5100,
   "ultimo_motivo_de_espera": "cota", "expiradas_24h": 0,
   "breaker": {"anthropic": "fechado"}}
]
```

Fontes, todas existentes: `em_execucao`/`em_espera` dos contadores Redis do §8.2; `p95`/`mediana` de `messages.payload.turn.total_ms` (§5.1) cruzado com `conversations.company_id`; `expiradas_24h` do contador; `breaker` da chave do §7.4.

Frontend: `app/admin/central-agentes/page.tsx:640` já consome esse endpoint — **uma seção nova na página que existe**, sem tela nova. ⛔ Nada de conteúdo de conversa atravessa: só contagens, estados, ids e tempos, como o módulo já faz.

⚠️ **`expiradas_24h` é o número que o Founder deve olhar todo dia.** Ele responde, sozinho, à pergunta que hoje não tem resposta: *"perdi alguma mensagem?"*.

**GATE F.** ① o bloco aparece com dois `company_id` distintos e os números batem com os contadores; ② um `company_id` de outra corretora **nunca** aparece na resposta de quem não é master admin (a rota já é `require_master_admin` — o guarda prova que continua); ③ `next start` + uma requisição a `/api/admin/spec034/agents-status` responde 200 (CLAUDE.md §9.1).
**MUTAÇÃO F.** remover o filtro de tenant da consulta de p95 → ① fica **vermelho** (os números das duas corretoras se fundem).

---

## 11. BLOCO G — a prova: duas corretoras, uma travada de propósito

### 11.1 A ordem canônica dos tenants

Canário e testes usam, nesta ordem (CLAUDE.md §12): **Amandus → Resulta → AutoFleet**. Para esta SPEC a exigência é mais forte: **duas corretoras ao mesmo tempo**, com TESTE-A numa e TESTE-B na outra.

### 11.2 O atraso injetado — o único mecanismo novo que degrada de propósito

```python
# backend/app/tasks/buffer_processor.py
def _atraso_de_teste_ms(company_id: str) -> int:
    """💭 Só para a prova de isolamento. FAIL-CLOSED por construção:
    lista vazia = ninguém (o desenho de JANELA_SILENCIO_EXCECOES, commit 05f46a9).
    Fora da allowlist → 0 e NÃO dorme."""
    permitidas = {c.strip() for c in os.getenv("ISOLAMENTO_ATRASO_ALLOWLIST", "").split(",") if c.strip()}
    if company_id not in permitidas:
        return 0
    return _env_int("ISOLAMENTO_ATRASO_MS", 0, minimum=0)
```

⛔ **Em produção a variável fica vazia, e o guarda G10 exige que o valor default produza ZERO atraso** — é o guarda que impede este mecanismo de virar um defeito.

### 11.3 Os casos mínimos do canário

| # | o quê | o que prova |
|---|---|---|
| 1 | **antes**: TESTE-A na corretora 1 manda 3 mensagens; medir `total_ms` | a linha de base, sem doente |
| 2 | **durante**: corretora 2 com `ISOLAMENTO_ATRASO_MS` alto + rajada sintética de 20 conversas de teste; **ao mesmo tempo**, TESTE-A na corretora 1 manda 3 mensagens | 🔴 **o gate**: o `total_ms` do caso 2 ≤ caso 1 + X (§5.4) |
| 3 | TESTE-B na corretora 2 (a doente) manda 1 mensagem | ele é atendido — **lento, mas atendido**, e o `payload.turn` diz `adiado`/`cota`, não `failed` |
| 4 | rajada de 50 mensagens de TESTE-B em 30 s | entrada = saída + retidas; `expiradas` = **0** |
| 5 | breaker aberto na corretora 2 (provedor derrubado por variável apontando para host inválido) | a corretora 1 **não sente**; o dono da 2 recebe **um** aviso; nada chega ao segurado |
| 6 | **depois**: `ISOLAMENTO_ATRASO_ALLOWLIST` esvaziada; repetir o caso 1 | o produto volta ao normal, e a prova disso é o mesmo número do caso 1 |

🧑 **O que só o Founder faz:** parear TESTE-A e TESTE-B em duas corretoras de teste distintas; ligar/desligar as variáveis do canário; clicar Implantar.

**GATE G.** os seis casos com saída real colada no relatório, com aliases, e o número do caso 2 comparado ao do caso 1 pelo X do BLOCO 0.
**MUTAÇÃO G.** rodar o caso 2 com a cota desligada → o gate fica **vermelho** e o relatório mostra os dois números. 🔴 **Esta mutação é obrigatória: é a única prova de que o gate consegue ficar vermelho.**

---

## 12. Guardas e mutações — 10 novos, teto 12 (D-PILOTO-14)

Todos sobre o **MOTOR** e sobre o **ACERVO real** (CLAUDE.md §9.4). ⛔ Proibido teste que reimplementa a regra: um teste que recalcula o rodízio em vez de chamar `ordenar_em_rodizio` prova outra coisa.

| # | guarda | onde | a mutação que o deixa VERMELHO |
|---|---|---|---|
| **G1** | `prontas()` e `should_process()` concordam sobre 20 buffers do corpus | `processar_buffers_prontos` real | `prontas` com régua própria |
| **G2** | `ordenar_em_rodizio` intercala e é **determinística** entre execuções | a função real | devolver a ordem do SCAN |
| **G3** | 50 chaves de A + 4 de B → as 4 de B terminam dentro de X; **com linha de controle** (a mesma rodada sem A) | motor com dublês | `cota_por_corretora` altíssima |
| **G4** | a cota é adquirida **antes** do teto global | motor, com dois contadores de ocupação | inverter a ordem |
| **G5** | o teste de paralelismo existente continua verde (`test_midia_e_concorrencia_do_webhook.py:519`) | teste que **já existe** | chave da cota sem o escopo |
| **G6** | os 4 construtores da fábrica recebem `timeout` e `max_retries`; zero `httpx.AsyncClient()` sem timeout | kwargs reais + varredura | tirar `timeout` de um construtor |
| **G7** | 🔴 200 chaves, cota 4: `expiradas == 0` e entrada = processadas + adiadas | motor | `adiar` vira `pass` |
| **G8** | não-líder não inicia o agendador; Redis fora → nenhum job de **envio** roda | dois processos reais | fail-open no `handoff_watchdog` |
| **G9** | 401 não entra no backoff; breaker abre na 5ª e fecha depois de T | a política real | aplicar backoff ao 401 |
| **G10** | 🔴 sem `ISOLAMENTO_ATRASO_ALLOWLIST`, o atraso é **ZERO** para qualquer `company_id` | a função real | default virar "todos" |

⚠️ **G3, G5 e G10 são os três que não podem ser negociados**: G3 é o outcome, G5 é a linha de controle herdada da 001.2, G10 é a trava do mecanismo perigoso desta SPEC.

⚠️ **Mutação roda em worktree próprio ou com lock exclusivo, restaura por CÓPIA, nunca `git checkout`** (protocolo §10). A bateria inteira **não** roda enquanto um juiz muta.

---

## 13. Migrations

📊 **Nenhuma migration prevista.** Tudo o que esta SPEC grava cabe onde já há lugar:

- o turno do atendimento → `messages.payload` (jsonb, já existe; o chat já grava `turn` ali)
- contadores de fila e espera → Redis (trânsito, CLAUDE.md §6)
- o lock de líder → Redis
- o breaker → Redis
- a Central → o JSON do endpoint que já existe

🔴 **Se o executor concluir que precisa de SQL**, lê `docs/canon/MIGRATIONS-AUTHORITY.md` **antes**, escreve **APPLY / VERIFY / ROLLBACK** antes de rodar, e registra em `CHANGE-ADDENDA.md` como mudança além do texto da SPEC. ⚠️ Índice e GRANT disparam o piso CRÍTICO (protocolo §3.2) — só o COMMENT é isento.

---

## 14. Canário controlado em produção

### 14.1 Antes

Confirmar TESTE-A e TESTE-B, cada um na **sua** corretora de teste; conferir o remetente real sem tocar QR operacional; fixar janela e orçamento; provar os bloqueios com saídas simuladas **antes** de qualquer envio vivo.

🔴 **Se os dois números estiverem na mesma corretora, o canário não prova isolamento.** O executor registra isso como **PARCIAL com nome** — ⛔ nunca converte em verde, e ⛔ nunca "liga a corretora operacional só para medir" (§1.3).

### 14.2 Durante

Os seis casos da §11.3, nesta ordem, com o antes e o depois. Nenhum envio fora da allowlist, inclusive por alerta, fila, reenvio e resposta automática.

### 14.3 Depois

Esvaziar `ISOLAMENTO_ATRASO_ALLOWLIST`; conferir que nenhuma intenção do canário ficou pendente; repetir o caso 1 e mostrar que o número voltou; preservar os logs sem PII; entregar as evidências com aliases.

### 14.4 Validação com Saionara e Regina

Esta SPEC **não muda o que elas veem**, exceto pelo aviso do §8.3 e pelo bloco da Central (§10). O que se valida com elas é só isso: a frase do aviso soa humana? o bloco por corretora responde *"perdi alguma mensagem?"* sem explicação? O Founder conduz; o executor não as contata.

---

## 15. Entrega, implantação e rollback

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR. (CLAUDE.md §2)
git rev-list --count origin/main..HEAD
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do push, colada no relatório. Commit **arquivo por arquivo** — ⛔ nunca `git add -A`.

```
ORDEM DE IMPLANTAÇÃO:  smith-api  →  smith-web   (o portal-worker não muda)
ROLLBACK, em 3 variáveis:
   WHATSAPP_COTA_POR_CORRETORA = um número muito alto   → a cota deixa de morder
   LLM_TIMEOUT_SEGUNDOS = 0                             → volta o comportamento do SDK
   SCHEDULER_ENABLED = true em todas as réplicas        → volta o comportamento de hoje
🔴 Reverter código não desfaz mensagem enviada. Preservar evidência e impedir repetição.
```

⚠️ **Mexeu em `app/` do frontend:** `npm run test:rotas-montam` + `next start` + **uma requisição a `/api/…`** antes de declarar gate verde (CLAUDE.md §9.1).

| marco | evidência exigida |
|---|---|
| implementado e gateado | commit, G1–G10 verdes, as 10 mutações vermelhas com o nome da falha nova |
| entregue na `main` | SHA remoto e a saída do `git push` |
| implantado | serviço/imagem/SHA + `/health` respondendo, com `scheduler: "lider"` |
| validado no canário | os 6 casos da §11.3, por alias, com os números lado a lado |
| ativado em corretora operacional | 🧑 fora da autorização desta execução |

---

## 16. Documentação e acompanhamento obrigatórios

1. **Relatório** em `docs/canon/reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md`, pelo template, **abrindo com o EXECUTION CARD** e com a telemetria de 5 linhas (protocolo §11).
2. **`PENDENCIAS.md`** — re-julgar por número, com prova: **P-PILOTO-01** (a origem) · **P-096-STOP-MULTIPROCESSO** (`:10255`) · **P-237** (`:8167`) · **P-238** (`:8183`) · **P-207** (`:5594`) · **P-248** (`:8774`). Cada uma: `FECHADA` com a prova · `CONTINUA` com o que destrava · `MORREU`.
3. **`ESTADO-DAS-SPECS.md`** e **`EXECUTION-MASTER-PLAN.md`**.
4. **`CHANGE-ADDENDA.md`** — tudo além do texto da SPEC, classificado BLOCKER · ESSENCIAL · VALIOSA · FUTURA, **antes** de executar.
5. **`FOUNDER-DECISIONS.md`** — só se nascer decisão nova (💭 candidata: o X do §5.4 vira o primeiro SLO declarado do projeto).
6. **Dossiê:** https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 — ler o HTML publicado **inteiro** antes de republicar com a mesma `url`; aba **Pilotos**. Sem ferramenta ou sem acesso: atualizar `docs/canon/reports/dossies/dossies-autobrokers.html` e dizer **"publicação pendente"** com o passo exato. ⛔ Nunca alegar que o link foi atualizado.

---

## 17. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> 🔴 O pesquisador (protocolo §7.3) **reabre** as três e escreve a data da reabertura na SPEC definitiva. Abaixo, o que a leitura de **13/09/2026** encontrou.

### E1 — Microsoft · Bulkhead pattern
**URL:** https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead · reaberta 13/09/2026
**O que faz:** particiona recursos por consumidor para que a falha de um não se propague. Nomeia o mecanismo do nosso elo ④ com todas as letras: *"the client's connection pool might be exhausted. At that point, the consumer's requests to other services are affected"*, e *"Many requests from one client might exhaust available resources in the service… which causes a cascading failure effect"*. Recomenda, para partir consumidores, *"processes, thread pools, and semaphores"*, e diz que bulkhead se combina com *"retry, circuit breaker, and throttling patterns"*.
**O que MODELAMOS:** dois pontos. ① **Semáforo por consumidor** = a cota por corretora do §6, com o consumidor sendo o `escopo` da chave do buffer. ② **Thread pool dimensionado** = `EXECUTOR_THREADS` do §9.3 — é a partição que o documento manda fazer primeiro e a que hoje não existe.
**O que REJEITAMOS:** *"deploying them into separate virtual machines, containers, or processes"* como forma **desta** SPEC. Um contêiner por corretora é a granularidade que o próprio texto manda escolher com cuidado (*"determine the level of granularity"*) e que, com duas corretoras piloto, custaria mais do que entrega. Fica em §18 com gatilho.
**Como o juiz inspeciona:** abre a página, confere que "Problems and considerations" cita semáforos e thread pools, e compara com `_atualizar_cota`/`set_default_executor` no diff.

### E2 — Kubernetes · API Priority and Fairness
**URL:** https://kubernetes.io/docs/concepts/cluster-administration/flow-control/ · reaberta 13/09/2026
**O que faz:** é a implementação de referência de **cota + fila justa** num sistema multi-inquilino real. O limite global de concorrência é *"divided up among a configurable set of priority levels"*, e cada nível *"will only dispatch as many concurrent requests as its particular limit allows"*; dentro do nível, *"a fair-queuing algorithm prevents requests from different flows from starving each other"*. O objetivo declarado é o nosso, palavra por palavra: *"a poorly-behaved [controller] need not starve others"*.
**O que MODELAMOS:** ① **teto global repartido em cotas** — é exatamente o §6.3 (cota da corretora dentro do teto do processo), e é a razão de a nota do "pool por corretora sem teto global" ser 62. ② *"introduces a limited amount of queuing, so that no requests are rejected in cases of very brief bursts"* → o §8: a rajada **espera**, não é recusada nem perdida.
**O que REJEITAMOS:** ① **borrowing** (nível ocioso emprestar concorrência ao saturado) — com 2 corretoras a complexidade não paga, e emprestar é a porta pela qual a interferência volta; entra em §18 quando houver dezenas de corretoras. ② **shuffle sharding** — resolve *quem divide fila com quem* quando há mais inquilinos que filas; a nossa cota é nominal por `escopo` e não precisa de sorteio.
**Como o juiz inspeciona:** abre a página, lê a seção "Concepts", e confere que a nossa cota é subdivisão de um teto (e não um teto novo por corretona) lendo a ordem de aquisição em `_uma`.

### E3 — Redis · `SET` (NX/EX) e o script de soltura
**URL:** https://redis.io/docs/latest/commands/set/ · reaberta 13/09/2026
**O que faz:** documenta que `SET resource-name anystring NX EX max-lock-time` *"is a simple way to implement a locking system with Redis"*, e prescreve, literalmente, as duas correções que fazem dele um lock honesto: *"Instead of setting a fixed string, set a non-guessable large random string, called token"* e *"Instead of releasing the lock with DEL, send a script that only removes the key if the value matches"*, com o script:
```lua
if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) else return 0 end
```
**O que MODELAMOS:** o **lock de líder do agendador** (§9.2): token aleatório, `EX 60`, renovação a cada 20 s, soltura pelo script literal. É o mesmo padrão que `portal_worker/leases.py:130-145, :421` já roda em produção — reaproveitamos a forma, não copiamos o arquivo (aquele é lease por conta de portal).
**O que REJEITAMOS:** ① **Redlock** (que a própria página recomenda por cima do `SET NX`): temos **um** Redis, não N independentes; Redlock sem N mestres é cerimônia sem garantia. ② **Redis Streams com consumer group** para o atendimento — foi lida (https://redis.io/docs/latest/develop/data-types/streams/, mesma data) e **rejeitada de propósito**: o padrão já existe no repo (`app/services/work/queue.py:26-116`, com `xreadgroup`/`xautoclaim`/`xack`) e serve Work Runs; trazê-lo para o WhatsApp criaria uma segunda fila sobre a mesma mensagem, que é o motor paralelo do CLAUDE.md §5. O buffer no Redis **já é** a fila e o `GET+DEL` em pipeline **já é** a entrega única.
**Como o juiz inspeciona:** abre a seção "Patterns" da página, compara o Lua do diff caractere a caractere com o da doc, e confirma que não há `DEL` cego no caminho de soltura.

---

## 18. O QUE SAIU, E QUANDO VOLTA

| frente | por que não entra agora | gatilho de retorno |
|---|---|---|
| **executor de threads por caminho** (bulkhead completo) | mudaria 306 chamadas de `to_thread`; o ganho é desconhecido antes de medir | o BLOCO 0 mostrar o poço saturado sob a carga do §5.3 |
| **rate limit por corretora na ENTRADA do webhook** (hoje por IP: `webhook.py:1387`, `rate_limit.py:28`) | a entrada não é o gargalo medido; e o IP é do provedor, então a chave certa é o `escopo`, que só é conhecido depois do auth | uma corretora estourar o balde e calar as outras — vira pendência com o número |
| **`uvicorn --workers N` / réplicas da API** | 📊 P-096-STOP-MULTIPROCESSO: `TURNOS_ATIVOS` é memória de processo e o `/chat/stop` cairia noutro worker | fechar P-096-STOP-MULTIPROCESSO |
| **serviço `smith-jobs` separado** | depende de 🧑 criar o serviço no EasyPanel | o Founder criar o serviço; o código já sai pronto (§9.4) |
| **borrowing entre corretoras** (E2) | com 2 corretoras não paga, e é por onde a interferência volta | dezenas de corretoras com carga desigual medida |
| **Prometheus / OpenTelemetry** | 📊 zero instrumentação hoje (`grep -rni "prometheus\|opentelemetry\|statsd" backend/app` → 2, ambos comentário bibliográfico); a Central resolve o que esta SPEC precisa | uma SPEC de operação que precise de série temporal, não de instantâneo |
| **pool de banco por corretora** | o Supabase é acessado por service role com pool único; partir isso é SPEC própria | saturação de conexões medida |
| **breaker de portal** | é da **EXTRA-001.6 §B3.3**, já escrita | — (não volta; só se referencia) |

🔴 **Nada da §2.1 sai em silêncio.** Se a conversão mostrar conflito material, registra-se proposta de mudança em `CHANGE-ADDENDA.md` — recorte unilateral não se chama "otimização AAA" (CLAUDE.md §11).

---

## 19. Fila depois desta entrega

Ordem canônica (DIAGNÓSTICO §12.1): `001.0 → 001.6-P0 → 001.1 → 001.2 → 001.3 → 001.4 → 001.6 → 001.7 → 001.10 → 001.5 → **001.8 (esta)** → 001.9`.

| para quem | o que esta SPEC deixa pronto |
|---|---|
| **001.7** (piloto medido) | 🔴 o `payload.turn` do atendimento e o p95 por corretora — é a régua que a 001.7 precisa e que hoje não existe |
| **001.9** e a SPEC de painel | a seção por corretora da Central, onde as métricas de operação passam a morar |
| **SPEC-101 / EXTRA-002/008/009** | a cota por `escopo` vale para qualquer adaptador: um conector lento de uma corretora não trava a outra |
| qualquer SPEC futura com job periódico | o lock de líder, que deixa de ser decisão de cada job |

⚠️ **A 001.8 vem depois da 001.2 e não antes** — a trava de turno é pré-requisito (§3.3). Vir depois da 001.7 seria pior: sem o `payload.turn` do atendimento, a 001.7 mede a operação com régua emprestada do chat.

---

## 20. DEFINIÇÃO FINAL DE CONCLUSÃO — lista fechada e verificável

```
[ ]  1. EXECUTION CARD no topo do relatório, com o X do §5.4 preenchido e o comando ao lado
[ ]  2. BLOCO 0: as 16 premissas remedidas, com comando e valor de hoje — inclusive o item 9
        (cpu_count/threads DENTRO do smith-api implantado)
[ ]  3. G1–G10 verdes, e as 10 mutações VERMELHAS, cada uma com o nome da falha nova em subprocesso
[ ]  4. o teste de paralelismo que já existe (`test_midia_e_concorrencia_do_webhook.py:519`)
        continua VERDE — a linha de controle herdada da 001.2
[ ]  5. `expiradas == 0` sob a carga do §5.3 e no caso 4 do canário
[ ]  6. o canário: os 6 casos da §11.3, com TESTE-A e TESTE-B em CORRETORAS DIFERENTES,
        e o número do caso 2 comparado ao do caso 1 — ou o PARCIAL nomeado da §14.1
[ ]  7. `ISOLAMENTO_ATRASO_ALLOWLIST` vazia no implantado, conferida DEPOIS do canário
[ ]  8. a suíte inteira, 2 a 4 vezes na SPEC, com a contagem no relatório
[ ]  9. `next start` + uma requisição a `/api/…` respondendo 200 (mexeu na Central)
[ ] 10. `git push origin HEAD:main` com a saída COLADA; `/health` do implantado com `scheduler`
[ ] 11. PENDENCIAS: as 6 da §16.2 re-julgadas com prova; pendências novas registradas
[ ] 12. dossiê republicado na MESMA url, ou "publicação pendente" com o passo exato
```

🔴 **Um item aberto = SPEC aberta.** "Quase tudo verde" não é um estado.

---

## 21. 📋 CAIXA DO FOUNDER — o que só o Founder faz, e o que o executor NÃO espera

| # | o que é | o que custa esquecer | bloqueia? |
|---|---|---|---|
| 1 | **Parear TESTE-A e TESTE-B em duas corretoras de teste distintas** | sem isso o canário não prova isolamento, só latência | **SÓ o §14**; os blocos A–F seguem |
| 2 | Ligar e desligar `ISOLAMENTO_ATRASO_ALLOWLIST` no canário | o atraso injetado é o único mecanismo que degrada de propósito | só o §11.3 |
| 3 | Definir as variáveis novas no smith-api (§9.4) e clicar **Implantar** | o código sobe com os defaults; funciona, mas não com o número medido | não |
| 4 | Decidir se cria o serviço `smith-jobs` | capacidade, não isolamento. O código já sai pronto | não |
| 5 | Aceitar o **X** do §5.4 como o primeiro SLO declarado do projeto | sem número, "nenhuma interferência" não é verificável | não — o executor escolhe e registra (protocolo §9) |

⛔ **Nunca parar para entregar uma linha desta caixa** (protocolo §9).

---

> **O resultado, em uma frase:** quatro segurados de cada corretora são atendidos ao mesmo tempo; a corretora com o modelo lento espera sozinha; e a pergunta *"perdi alguma mensagem hoje?"* passa a ter uma resposta, que é **zero**.
