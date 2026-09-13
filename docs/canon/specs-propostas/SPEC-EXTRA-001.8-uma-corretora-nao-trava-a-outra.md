# SPEC-EXTRA-001.8 — UMA CORRETORA NÃO TRAVA A OUTRA
## Cota por corretora · rodízio · teto por chamada · contrapressão que não perde mensagem

**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica nem implementação.
**Versão:** 1.0 · **13/09/2026** · **Baseline:** worktree `AutoBrokers-FIX`, HEAD `53a22c3`, 📊 `git rev-list --count HEAD..origin/main` → 0. Todas as linhas citadas foram reabertas hoje; o BLOCO 0 as remede.
**Branch:** `feat/spec-extra-001.8-isolamento-por-corretora` · **SPEC definitiva:** `docs/canon/specs/SPEC-EXTRA-001.8-uma-corretora-nao-trava-a-outra.md` · **Relatório:** `docs/canon/reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md` · **Research Pack:** `SPEC-EXTRA-001.8-uma-corretora-nao-trava-a-outra-RESEARCH-PACK.md`.
**Origem:** DIAGNÓSTICO §3 bloco 001.8 e §12.1 linha 11 · **P-PILOTO-01** · **D-PILOTO-07** · `PLANO-PILOTOS-AJUSTES-2026-09-08.md` §2.1.
**Depende de:** **EXTRA-001.2** §5 (trava de turno por conversa). Esta SPEC **pendura** nela e não a duplica — §3.3.

---

## 0. Resultado e motivo

> Quatro segurados da Resulta e quatro da AutoFleet falam ao mesmo tempo. Os oito são atendidos. Se o modelo da Resulta ficar lento, se o portal dela travar, ou se um número mandar cinquenta mensagens seguidas, **a AutoFleet não sente nada** — e nenhuma mensagem se perde: o que não cabe agora espera, com o "digitando…" ligado e uma linha dizendo por quê.

📊 **O que os pilotos mediram:** o agente ficou ligado **~1h53 em três dias**, falou com **5 segurados**, e **nunca** houve duas corretoras atendendo ao mesmo tempo (DIAGNÓSTICO §0). Ou seja: **o defeito desta SPEC nunca foi observado em produção — foi lido no código.** Isso muda o gate: a prova não pode ser "não aconteceu de novo"; tem de ser **uma corretora travada de propósito, medida contra a outra**.

🔴 **Por que é CRÍTICO mesmo sem incidente:** P-PILOTO-01 registra o custo, palavra do Founder — *"com centenas de corretoras, um travamento em uma para todas — irreparável para a AutoBrokers"*. Defeito de isolamento não avisa: aparece no primeiro dia em que o produto dá certo.

### 0.1 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | decisão | efeito nesta SPEC |
|---|---|---|
| **D-PILOTO-07** | *"≥ 4 atendimentos simultâneos por corretora e nenhuma corretora interferindo em outra"* | **4 é o piso da COTA**, não o teto do sistema (§6.2). "Nenhuma interferência" vira número medido (§5.4) |
| **D-PILOTO-14** | AAA opção B; **≤ 12 guardas novos**; bateria sobre motor e acervo real | §12 gasta **10**. Os 2 restantes são para o que o painel achar — ⛔ não para preencher |
| **D-PILOTO-06** | as entregas de 08/09 saíram sem AAA | o semáforo de `buffer_processor.py` nasceu ali e é **alívio, não solução** (texto do Founder em P-PILOTO-01). Esta SPEC termina o trabalho |
| **D-PILOTO-20** | criação neste chat, **execução em chat novo** sob AAA opção B | o `PROMPT-DE-ABERTURA-EXTRA-001.8.md` é o que o Founder cola |
| **D-PILOTO-02** | a atendente responder pelo celular pausa o robô, e isso é o desejado | conversa pausada não pode ocupar cota (§6.4) |

### 0.2 EXECUTION CARD — proposto, a confirmar no BLOCO 0

```text
OUTCOME .............. 4+ atendimentos simultâneos POR CORRETORA; uma corretora lenta, travada
                       ou em rajada não muda a latência da outra; zero mensagem perdida
RISCO ................ 8  (ALCANCE 3 o segurado · REVERSIBILIDADE 3 a mensagem sai do prédio ·
                          FREQUÊNCIA 2 todo atendimento)
SUPERFÍCIE ........... 2  (vários comportamentos + peças novas: cota, rodízio, teto, breaker)
PISO APLICADO ........ §3.2 "qualquer coisa que ENVIE" — o caminho alterado é o que responde ao
                       segurado. O piso já daria CRÍTICO sozinho
NÍVEL ................ CRÍTICO — opção B
UNIDADES ............. 7  (A medição · B cota+rodízio · C teto/retry/breaker · D contrapressão ·
                          E processos e líder · F observabilidade · G prova)
COESÃO ............... `buffer_processor.py` é ARQUIVO-HUB (A, B, D, F escrevem nele): UM dono por
                       vez. `llm_factory.py` é o hub de C. F e G são disjuntos do resto
PARALELISMO REAL ..... no máximo 2 escritores: {C llm_factory+graph} ∥ {A/B/D buffer_processor}.
                       E e F entram depois, em série
TIME ................. investigador+pesquisador (1) · desenhista · builder(s) · 3 lentes de ASSUNTO
                       DIFERENTE (dado · código · produto) · red team · 1 juiz fresco (§6.1)
REFERÊNCIA ........... interna: `backend/app/workers/smith_worker.py:252-278` (a cota por tenant que
                       JÁ existe em produção) + `backend/tests/test_midia_e_concorrencia_do_webhook.py:519`
                       (a LINHA DE CONTROLE do paralelismo) · externas: §17 E1–E3
GATES ................ G1–G10 da §12, cada um com a mutação que o deixa vermelho
O ELO ................ §0.3
FAIXA DE RELÓGIO ..... 💭 8–12 h
ORÇAMENTO ............ 💭 ≤ 2,5 M tokens de subagentes. Estourou → menos LENTES, nunca menos MUTAÇÃO
```

🔴 **BLOCKER nesta SPEC** (teste do produto, protocolo §2): qualquer achado em que **uma corretora muda o que a outra recebe** — latência, silêncio, mensagem perdida ou duplicada. É isolamento (CLAUDE.md §7) e **não se rebaixa a pendência** (protocolo §6). Nome de variável, formato de log e tela são pendência, e seguem.

### 0.3 🔴 O ELO — onde exatamente uma corretora alcança a outra

A afirmação é *"A atrasa B **porque** compartilham recurso sem partição"*. Medi A, medi B, e medi **que B chega em A**: são **quatro** recursos compartilhados, e três ninguém tinha apontado.

```
① O SEMÁFORO DE 6 É GLOBAL, E ENVOLVE ATÉ A CONFERÊNCIA BARATA
   buffer_processor.py:76-77  semaforo = asyncio.Semaphore(limite)   # limite = 6
   buffer_processor.py:79-83  async with semaforo:  →  await buffer_service.should_process(chave)
   🔴 A conferência de prontidão (um GET no Redis, ~1 ms) está DENTRO do semáforo, atrás de até
   6 turnos de LLM. Com 4 conversas da Resulta em voo a 10 s cada, a da AutoFleet não fica atrás
   na fila: ela NEM É OLHADA por 10 s. O elo não é "esperar a vez" — é "não existir para o varredor".

② A LISTA É UMA SÓ, SEM AGRUPAMENTO E SEM ORDEM
   buffer_processor.py:126-141  redis.scan(match="whatsapp_buffer:*") → chaves.append(...)
   buffer_processor.py:97       asyncio.gather(*(_uma(c) for c in chaves))
   📊 Zero `sort`, zero agrupamento por corretora, zero rodízio. A ordem é a do SCAN — ordem de
   slot, arbitrária. 50 chaves da Resulta e 1 da AutoFleet: a da AutoFleet cai onde calhar.

③ O RELÓGIO NÃO EXISTE EM NENHUM PONTO DO TURNO
   📊 grep -n "wait_for\|timeout" backend/app/tasks/buffer_processor.py  →  ZERO linhas
   📊 grep -rn "timeout\|max_retries" backend/app/factories/             →  ZERO linhas
   graph.py:1603  await graph.ainvoke(...)   ·   graph.py:2062  graph.astream_events(...)
   Uma chamada pendurada segura 1 dos 6 slots até o SDK desistir — e é o SDK que decide, não nós.

④ O POÇO DE THREADS É UM SÓ, E NINGUÉM O DIMENSIONOU
   📊 306 `asyncio.to_thread` em 64 arquivos (24 só no webhook.py); 📊 ZERO `set_default_executor`.
   `asyncio.to_thread` usa o executor default: ThreadPoolExecutor(min(32, cpu_count()+4)).
   Num contêiner de 1 vCPU são 5 threads para TODAS as corretoras, TODAS as leituras ao Supabase
   e os 24 jobs do agendador. 🔴 É o recurso que o Bulkhead (§17 E1) manda partir primeiro, e o
   único cujo tamanho o repositório NÃO SABE — depende do `cpu_count` do contêiner. BLOCO 0 mede.
```

⚠️ **Um quinto elo que NÃO entra:** o rate limit do webhook é **por IP** (`webhook.py:1387` `@limiter.limit("120/minute")`, `rate_limit.py:28` `key_func=get_real_client_ip`) — todas as corretoras do mesmo provedor dividem o balde. Mas é balde de **entrada**, e a entrada não é o gargalo medido. Vai para pendência com o número (§18).

---

## 1. AUTORIZAÇÃO DE TESTES

### 1.1 Allowlist

**TESTE-A** e **TESTE-B** vêm da allowlist privada do Founder, por variável de ambiente. ⛔ Nunca commitar, imprimir, logar ou publicar os números; nas evidências, sempre o alias.

🔴 **O que esta SPEC exige e as outras não:** os dois números em **CORRETORAS DIFERENTES ao mesmo tempo** — é a única forma de provar isolamento. Se estiverem na mesma corretora, **o canário não prova nada**, e o executor diz isso em vez de declarar verde (§14.1).

### 1.2 Autorizado

```
✅ ler o repositório · rodar a suíte · scripts read-only
✅ SELECT em produção, só contagens e tempos — NUNCA conteúdo de mensagem
✅ escrever código, testes e documentação · commit e push na branch da SPEC
✅ teste de carga SINTÉTICO contra o motor, com dublês (§5.3) — zero provedor externo
✅ no canário e só nele: conversas entre TESTE-A e TESTE-B, em corretoras de teste
```

### 1.3 Proibido

```
⛔ mensagem a segurado, seguradora, atendente ou grupo real
⛔ número operacional da Resulta ou da AutoFleet como remetente
⛔ carga contra a API de LLM, contra a Evolution ou contra portal de seguradora
⛔ ligar o agente em corretora operacional "só para medir"
⛔ imprimir CPF, CNPJ, telefone, placa, nome de segurado, e-mail ou credencial
⛔ deixar a flag de atraso injetado (§11.2) ligada fora do canário
⛔ merge na `main` sem o gate final
```

### 1.4 Verificação antes de cada efeito

Ambiente + tenant de teste + conexão fixada + identidade real do remetente + destino normalizado + **a flag de atraso está ligada SÓ para o `company_id` de teste**. Identidade não confirmada → **não envia**, e não escolhe outra conexão sozinho.

🔴 **A trava própria desta SPEC:** o atraso injetado (§11.2) é o único mecanismo novo capaz de **degradar o produto de propósito**. Nasce fail-closed: sem `ISOLAMENTO_ATRASO_ALLOWLIST` com o `company_id` exato, devolve 0 ms e não dorme. Lista vazia = ninguém — o desenho de `JANELA_SILENCIO_EXCECOES` (commit `05f46a9`).

### 1.5 Falta de canal ou ação física

Continuar código, testes, gates e preparação. Para o Founder ficam: parear TESTE-A e TESTE-B em duas corretoras de teste, e dimensionar o serviço no EasyPanel (§9.4). **Ausência de canário não vira aprovação** — vira PARCIAL com o nome do que faltou.

---

## 2. Escopo e exclusões

### 2.1 Obrigatório

1. **Medir** a latência por etapa (webhook → buffer → grafo → LLM → envio) e o tamanho real dos quatro recursos do §0.3.
2. **Cota por corretora + rodízio** no processador atual; sem fila nova.
3. **Teto por chamada e por turno** no LLM e nas ferramentas; retry com backoff só em erro transitório; **breaker por provedor de LLM**.
4. **Contrapressão**: cota cheia → a mensagem espera; nunca se perde, nunca expira em silêncio; "digitando…" ligado; dono avisado quando a espera passa do combinado.
5. **Processos**: lock de líder em Redis para os 24 jobs do APScheduler; caminho preparado e nomeado para o Founder separar o serviço de jobs.
6. **Observabilidade por corretora** na Central de Agentes.
7. **Prova** com duas corretoras, uma travada de propósito.

### 2.2 Fora (tabela com gatilho de retorno em §18)

Troca de provedor de WhatsApp · multicanal · rate limit por corretora na entrada do webhook · executor de threads por caminho · fila nova em Redis Streams · autoscaling · Prometheus/OpenTelemetry · pool de banco por tenant · breaker de **portal** (é da 001.6) · trava de turno e pausa humana (são da 001.2).

---

## 3. Autoridades preservadas e arquitetura

🔴 **CLAUDE.md §5 proíbe criar em paralelo runtime, scheduler ou executor.** Esta SPEC não cria nenhum: ela **parte** o que já existe.

### 3.1 O que é reaproveitado, por arquivo

| peça | onde já mora | o que esta SPEC faz |
|---|---|---|
| processador de buffers | `backend/app/tasks/buffer_processor.py:63-110` | **estende**: cota por escopo + rodízio + teto por conversa. Mesma assinatura, parâmetros novos com default |
| a chave com tenant dentro | `backend/app/services/message_buffer_service.py:36-57` (`whatsapp_buffer:{escopo}:{telefone}`) | **lê** o escopo da chave. O isolamento já está lá desde a SPEC-063 Bloco H; faltava usá-lo para escalonar |
| **a cota por tenant** | `backend/app/workers/smith_worker.py:41` (`WORK_TENANT_CONCURRENCY`), `:58` (`_por_tenant`), `:263-278` (`_agendar`/`_liberar_slot`) | **copia a forma, não o código**: mesmo desenho (dicionário por `company_id`, teto, liberação no `done_callback`), já em produção para Work Runs. É a REFERÊNCIA INTERNA do card |
| fila durável com consumer group | `backend/app/services/work/queue.py:26-28, :78-79, :100, :116` (Streams, `xreadgroup`, `xautoclaim`, `xack`) | **lê e REJEITA** para o atendimento — §6.1. Não se cria fila nova nem se migra a existente |
| lock com `company_id` na chave | `backend/portal_worker/leases.py:286`, `:421` (`set(nx=True, ex=…)`), `:130-145` (Lua) | **copia o padrão** para o lock de líder (§9.2). ⛔ Nunca `DEL` cego |
| espaçamento por corretora | `backend/app/services/platform_outbound.py:119` (`platform_gate:{company_id}`), `:582-584` | **precedente** de chave Redis com tenant no caminho de envio; mesma convenção de nome |
| fábrica de LLM | `backend/app/factories/llm_factory.py:140-253` | **recebe** `timeout` e `max_retries` nos quatro construtores. Nenhuma fábrica nova |
| Central de Agentes | `backend/app/core/central_de_agentes.py` (cache Redis 60 s; linha 29: *"zero migration, zero tabela nova"*), `backend/app/api/admin_spec034.py:56-67`, front `app/admin/central-agentes/page.tsx:640` | **ganha um bloco por corretora**, respeitando a declaração do próprio módulo |
| trava de turno por conversa | **EXTRA-001.2 §5** (`abrir_turno`/`fechar_turno`, `whatsapp_turno:{escopo}:{telefone}`) | **pendura**: a cota entra ANTES da trava; a trava continua por conversa (§3.3) |

### 3.2 O contrato lógico, sem tabela nova

```text
SCAN whatsapp_buffer:*                          (o que já existe)
  → MGET em lote: quais estão prontas            (§5.2 — a conferência sai do semáforo)
  → agrupar por ESCOPO e intercalar               (§6.2 — o rodízio)
  → cota[escopo]  →  teto global                  (§6.3 — nesta ordem, e a ordem é a regra)
  → trava de turno da 001.2                       (por conversa, não por corretora)
  → get_and_clear (GET+DEL atômico, já existe)
  → processar COM TETO DE TEMPO                   (§7.2)
  → registrar o turno em messages.payload.turn    (§5.1 — o vocabulário do chat)
```

Supabase é a verdade durável; Redis é trânsito, lease e cache (CLAUDE.md §6). Nenhuma fila, publisher ou scheduler novo.

### 3.3 Onde esta SPEC encosta na 001.2, e onde para

A 001.2 §5.4 diz, com todas as letras: *"⛔ Trava por corretora é o defeito da EXTRA-001.8, não o conserto desta SPEC"*, e nomeia `backend/tests/test_midia_e_concorrencia_do_webhook.py:519` como **linha de controle** — o teste que prova que conversas diferentes continuam em paralelo.

```
001.2 entrega:  UMA resposta por rajada           → trava por (escopo, telefone)
001.8 entrega:  NENHUMA corretora trava a outra   → cota por escopo + rodízio + teto
```

🔴 **A ordem importa:** a cota é adquirida **antes** da trava de turno. Se fosse depois, uma conversa esperando a trava (porque outra rodada da mesma conversa está em voo) ocuparia um slot de cota da corretora — e a 001.2 teria criado, dentro da 001.8, o gargalo que a 001.8 existe para matar.

⚠️ **Se a 001.2 não estiver na `main`** (BLOCO 0 item 14): implementar a cota deixando o ponto de inserção da trava **escrito e vazio**, com a ordem documentada. ⛔ Não implementar a trava aqui — seria motor paralelo.

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código de produto

> **Este documento envelhece. O número do executor vence** (protocolo §5 ①).

| # | premissa | comando que a confere | valor de 13/09 |
|---|---|---|---|
| 1 | o semáforo é global e vale 6 | `sed -n '60,80p' backend/app/tasks/buffer_processor.py` | `_PARALELISMO_PADRAO = 6`; `Semaphore(limite)` na :77 |
| 2 | a conferência está dentro do semáforo | `sed -n '79,85p' …/buffer_processor.py` | `async with semaforo:` → `should_process` na :81 |
| 3 | zero timeout no processador | `grep -n "wait_for\|timeout" …/buffer_processor.py` | **0 linhas** |
| 4 | zero timeout/retry na fábrica de LLM | `grep -rn "timeout\|max_retries" backend/app/factories/` | **0 linhas** |
| 5 | o turno não tem teto | `grep -n "ainvoke\|astream_events" backend/app/agents/graph.py` | `:1603`, `:2062` — sem `wait_for` |
| 6 | 24 jobs, um processo, sem lock de líder | `grep -c "add_job" …/buffer_processor.py` · `grep -rn "advisory\|leader\|lider" backend/app \| wc -l` | **24** · **0** |
| 7 | uvicorn sem `--workers` | `grep -n CMD backend/Dockerfile` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 8 | 306 `to_thread` sem executor dimensionado | `grep -rn "asyncio.to_thread" backend/app \| wc -l` · `grep -rn "set_default_executor" backend/app` | **306** · **0** |
| 9 | 🔴 **quantas threads o contêiner tem** | `python -c "import os; print(os.cpu_count(), min(32,(os.cpu_count() or 1)+4))"` **rodado DENTRO do smith-api implantado** | ⛔ **DESCONHECIDO** — é o número mais importante do BLOCO 0 |
| 10 | a cota por tenant já existe para Work Runs | `sed -n '252,280p' backend/app/workers/smith_worker.py` | `CONCORRENCIA_POR_TENANT`, `_por_tenant`, `_liberar_slot` |
| 11 | Streams+consumer group já existem | `sed -n '26,30p;74,120p' backend/app/services/work/queue.py` | `STREAM_KEY`, `CONSUMER_GROUP`, `xreadgroup`, `xautoclaim`, `xack` |
| 12 | lease com tenant na chave já existe | `sed -n '86,96p;280,290p;415,425p' backend/portal_worker/leases.py` | TTL 120 s, `set(nx=True, ex=…)`, chave com `empresa` |
| 13 | TTL do buffer 60 s, teto de espera 25 s | `sed -n '73,76p' backend/app/core/config.py` | `DEBOUNCE=8 · MAX_WAIT=25 · TTL=60` |
| 14 | a trava de turno da 001.2 já está na árvore? | `grep -n "abrir_turno" backend/app/services/message_buffer_service.py` | **a confirmar** — muda §3.3 |
| 15 | latência real por etapa hoje | §5.1 | ⛔ **não existe registro no caminho do atendimento** |
| 16 | corretoras com agente ligado | `select count(*) from agents where agent_role='attendance' and is_active` | a remedir (📊 08/09: **3 de 3 desligados**) |

**GATE B0.** A matriz preenchida com o valor de hoje e o comando ao lado; o item **9** medido no serviço implantado, não na máquina do executor; o item **15** com a decisão registrada de qual sinal se usa. 🔴 **Item 9 ausente = o BLOCO E não pode ser dimensionado, e a SPEC diz isso em vez de chutar.**

**MUTAÇÃO B0.** O desenhista afirma no aquecimento, assinado, que *"o semáforo de 6 já é por corretora, porque a chave do buffer tem o escopo"*. O executor refuta com a linha 77 e explica que a chave isola **dados**, não **vez na fila**.

---

## 5. BLOCO A — a medição, antes de qualquer conserto

### 5.1 O relógio do atendimento passa a existir — com o vocabulário que já existe

📊 **Achado que reordena o bloco:** o turno **é** registrado, mas só no chat do painel. `backend/app/api/chat.py:1206-1223` monta `payload.turn` com `ttft_ms`, `total_ms`, `stages[]`, `attempt`, `status`, e (de `:1162-1167`) `finish_reason`, `usage`, `continuations`, `truncated`; gravado em `messages.payload` por `chat.py:938-958`. 🔴 **O caminho do atendimento (`webhook.process_whatsapp_message_background`) não grava nada disso.** Sem isso, "latência por etapa" não é medível e o gate da §11 não tem régua.

```python
# backend/app/api/webhook.py, na mensagem do AGENTE que já é gravada
payload["turn"] = {
    "status": "completed" | "failed" | "timeout" | "adiado",
    "total_ms": int,                       # do 1º evento do webhook ao envio aceito
    "etapas": [
        {"nome": "buffer_espera", "ms": int},   # last_at → saída do rodízio
        {"nome": "fila_cota",     "ms": int},   # espera pela cota da corretora
        {"nome": "grafo",         "ms": int},   # ainvoke inteiro
        {"nome": "envio",         "ms": int},   # whatsapp_service.send_message
    ],
    "provedor": str, "modelo": str,        # para o breaker do §7.4 ter a quem culpar
    "finish_reason": str | None, "usage": dict | None,   # os MESMOS nomes do chat.py
}
```

⛔ **Não criar um segundo vocabulário.** Se `chat.py` chama `total_ms`, o atendimento chama `total_ms`. Dois nomes para o mesmo fato é o defeito que CLAUDE.md §12.1 manda consertar no campo, não no texto.

O tenant chega por `conversations.company_id`, como no chat. 📊 `platform_sends(company_id, phone, kind, sent_at)` — migration `backend/supabase/migrations/20260720_02_spec045_platform_sends.sql:7-20`, índice `(company_id, phone, sent_at desc)` — continua sendo a contagem de **vazão de saída**, e não muda.

### 5.2 A conferência de prontidão sai de dentro do semáforo, e vira um só ida-e-volta

```python
# message_buffer_service.py — a regra continua UMA, e o lote a chama
def _esta_pronta(data: dict, agora: datetime) -> bool:
    """A regra de debounce extraída de `should_process` SEM mudar comportamento:
    8 s desde a última OU 25 s desde a primeira (pisos travados, :158/:166)."""

async def should_process(self, key: str) -> bool:
    """Fica: é o caminho de uma chave só, e a 001.2 o chama. Passa a delegar a `_esta_pronta`."""

async def prontas(self, chaves: list[str]) -> list[str]:
    """UM `MGET` para o lote; devolve as prontas, na ordem recebida.
    ⛔ NÃO consome o buffer: `get_and_clear` continua o único consumidor, e continua
    GET+DEL atômico (:183-186). Aqui só se PERGUNTA."""
```

🔴 **Por que isto é medição e não fila:** hoje cada varredura faz **um GET por conversa aberta, por segundo, atrás de um semáforo de 6**. É ao mesmo tempo o custo que ninguém contou e a causa do elo ① — e não dá para medir a fila de uma corretora enquanto a conferência da outra está presa atrás de um turno de LLM.

### 5.3 O teste de carga, sintético e reproduzível

`backend/tests/test_uma_corretora_nao_trava_a_outra.py` exercita `processar_buffers_prontos` — **o motor**, com dublês, como o teste existente já faz (`test_midia_e_concorrencia_do_webhook.py:61-89` carrega o módulo por AST).

```
corretora DOENTE   50 chaves, processador que dorme 10 s      (a rajada + o LLM lento)
corretora SADIA     4 chaves, processador que dorme 0,2 s
medir              tempo até a última chave SADIA ser processada
CONTROLE           a mesma rodada SEM a corretora doente      ← é ela que dá direito à conclusão
```

⚠️ **A linha de controle é obrigatória** (CLAUDE.md §9.2): sem a rodada sem a doente, um ambiente rápido "passaria" por acaso e o mérito iria para o lugar errado.

⛔ **Sem tenant de teste seguro, este bloco NÃO para.** A carga é 100% sintética (dublês de buffer e de processador; zero Redis real, zero LLM, zero envio) e roda em qualquer máquina. O que exige tenant real é só o canário da §14 — e esse é 🧑.

### 5.4 🔴 O X do gate sai daqui, e não de palpite

📊 `grep -c -i "p95" docs/canon/PENDENCIAS.md` → **0**. O projeto **não tem SLO declarado** — o protocolo §7.1 já o diz (*"⛔ o que NÃO temos: … alvo de latência (SLO)"*). D-PILOTO-07 pede "nenhuma interferência" e não dá número.

```
p95 da SADIA com a DOENTE presente   ≤   p95 da SADIA sozinha  +  X
X = 💭 2 s de partida, SUBSTITUÍDO pelo número medido no BLOCO 0 (proposta: p95 sozinha × 0,25)
```

🔴 **O X vai escrito no EXECUTION CARD do relatório, com o comando que o produziu** (CLAUDE.md §12.1).

**GATE A.** ① o turno do atendimento aparece em `messages.payload.turn` com `total_ms` e as 4 etapas, no canário; ② `prontas()` devolve exatamente o mesmo conjunto que `should_process` uma a uma, sobre 20 buffers do corpus; ③ o teste de carga imprime os dois p95 e a linha de controle.
**MUTAÇÃO A.** `prontas()` passa a usar régua própria (`>= 5 s`) em vez de `_esta_pronta` → ② fica **vermelho**. É assim que se prova que a regra continua sendo UMA.

---

## 6. BLOCO B — a cota por corretora e o rodízio

### 6.1 A decisão, com nota — e por que fila nova é a resposta errada

| opção | nota | por quê |
|---|---|---|
| **um pool com COTA por corretora + RODÍZIO, dentro do processador atual** | **91** | reaproveita o motor (CLAUDE.md §5), preserva o teto global (event loop e poço de threads continuam finitos), garante o piso de 4 da D-PILOTO-07 **e** que a vez chega. É a forma que o `SmithWorker` já usa em produção e que a k8s APF (§17 E2) implementa em escala |
| um pool POR corretora (semáforo dedicado, sem teto global) | 62 | dá isolamento e tira o teto: N corretoras × 4 estoura o event loop e o poço do §0.3 ④. Bulkhead sem admissão troca "uma trava todas" por "todas travam juntas" |
| **fila nova em Redis Streams por corretora** | **45** | ⛔ **motor paralelo.** O buffer no Redis **já é** a fila, e o `GET+DEL` em pipeline (`message_buffer_service.py:183-186`) **já é** a entrega única. 📊 Streams com consumer group já existem (`work/queue.py:26-116`) e servem Work Runs; duplicá-los para o WhatsApp criaria duas verdades sobre a mesma mensagem |
| subir `WHATSAPP_BUFFER_PARALELISMO` de 6 para 24 | 30 | mais slots para quem já monopoliza. Não é isolamento; é o mesmo defeito, mais caro |

🔴 **E a lição que o repositório já pagou:** `smith_worker.py:264-266` recusa a mensagem quando o tenant está no teto e **não dá `ack`** — a entrada fica no PEL do consumidor e só volta pelo `xautoclaim`, por tempo de ocioso. Com um worker só, a corretora no teto espera relógio, não vaga. **A nossa cota não herda isso:** o buffer **fica no Redis** e a varredura de 1 s o reencontra (§8.1).

### 6.2 O contrato

```python
# backend/app/services/message_buffer_service.py
@staticmethod
def escopo_da_chave(chave: str) -> str:
    """`whatsapp_buffer:{escopo}:{telefone}` → escopo.
    🔴 Chave malformada, ou escopo vazio/`sem-integracao` → "" (fail-closed).
    A recusa é a mesma da 001.2 §5.3 e pela mesma razão: duas corretoras com o mesmo
    telefone cairiam na mesma chave, e uma travaria a outra."""

# backend/app/tasks/buffer_processor.py
_COTA_PADRAO = 4                 # 🔴 D-PILOTO-07: o PISO é 4 por corretora
_PARALELISMO_PADRAO = 6          # fica o nome; o VALOR sobe (§9.3)

def ordenar_em_rodizio(chaves: list[str]) -> list[str]:
    """Agrupa por escopo e intercala: A1 B1 C1 · A2 B2 C2 · A3 …
    Determinística: dentro do escopo preserva a ordem recebida; entre escopos, ordem
    estável do escopo. ⛔ Não é aleatório nem por tamanho de fila — é rodízio simples.
    Sem determinismo o guarda G2 não consegue afirmar nada."""

async def processar_buffers_prontos(chaves, buffer_service, processar,
                                    paralelismo: int = 0,
                                    cota_por_corretora: int = 0,
                                    timeout_s: float = 0) -> dict:
    """Parâmetros novos, todos com default 0 = "leia do ambiente".
    ⚠️ A assinatura antiga continua válida: test_midia_e_concorrencia_do_webhook.py:519
    chama com `paralelismo=6` e `paralelismo=1` e TEM DE CONTINUAR VERDE (§3.3)."""
```

Variáveis novas, por nome: **`WHATSAPP_COTA_POR_CORRETORA`** (💭 4) · **`WHATSAPP_TURNO_TIMEOUT_S`** (§7.2). `WHATSAPP_BUFFER_PARALELISMO` já existe — 📊 e **não está definida em lugar nenhum** (nem `.env`, nem compose, nem docs), ou seja, em produção vale 6.

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
                return _adiar(chave, motivo="turno")     # o buffer FICA; 1 s depois tenta de novo
            try:
                buffer = await buffer_service.get_and_clear_buffer(chave)
                ...
                await asyncio.wait_for(processar(...), timeout=teto)   # §7.2
            finally:
                await buffer_service.fechar_turno(escopo, phone, token)
```

🔴 **Cota antes do teto global, sempre.** Se o teto global viesse primeiro, uma conversa esperando a cota da própria corretora estaria **segurando um slot global** — a corretora saturada passaria a consumir os 6 slots do processo só para esperar. É a inversão que transforma a proteção no defeito.

🔴 **Os semáforos por escopo nascem sob demanda e somem quando zeram** — o mesmo `_liberar_slot` do `smith_worker.py:272-278`. Um dicionário que só cresce é vazamento de memória com nome de isolamento.

### 6.4 O que NÃO ocupa cota

Conversa **pausada por intervenção humana** (D-PILOTO-02) e conversa dentro da **janela de silêncio** não chegam a `processar` — mas hoje chegam a ocupar um slot, porque o silêncio é decidido lá dentro. ⚠️ Esta SPEC **não move** a decisão de silêncio (é da 001.2/001.3). Ela **mede**: se o `total_ms` de uma conversa calada for < 50 ms, ela sai da cota na prática; se não for, vira **pendência com o número**, nunca conserto silencioso.

**GATE B.** ① 50 chaves de uma corretora + 4 de outra pelo motor real: as 4 terminam dentro de X (§5.4); ② `ordenar_em_rodizio` sobre 3 corretoras devolve intercalado e **estável entre execuções**; ③ `escopo_da_chave("whatsapp_buffer:sem-integracao:…")` → `""`, e a chave é adiada, não processada; ④ **o teste de paralelismo existente continua verde**.
**MUTAÇÃO B.** (a) cota removida (`cota_por_corretora=10_000`) → ① **vermelho**; (b) ordem invertida (global antes da cota) → ① **vermelho**; (c) rodízio trocado pela ordem do SCAN → ② **vermelho**.

---

## 7. BLOCO C — o relógio do modelo e das ferramentas

### 7.1 Teto por chamada, na fábrica

```python
# backend/app/factories/llm_factory.py — nos QUATRO construtores (:164, :200, :219, :230)
LLM_TIMEOUT_S   = int(os.getenv("LLM_TIMEOUT_SEGUNDOS", "0"))   # 0 = medido no BLOCO 0
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
```

📊 Hoje a fábrica passa só `model`, `max_tokens`, `api_key`, `callbacks`, `streaming`, `temperature` — **zero** `timeout`, **zero** `max_retries`. O SDK aplica o default dele, que nós não escolhemos e não medimos.

⚠️ **O teto não se inventa:** o BLOCO 0 mede o p95 do `total_ms` do chat (que **já** grava, `chat.py:1210`) e o teto nasce em **p95 × 3**, piso 60 s. 💭 Partida: 90 s. O número final vai no card com o comando.

### 7.2 Teto por TURNO, e a distinção que evita cortar quem está trabalhando

```
ATENDIMENTO (webhook, sem streaming ao segurado)
   asyncio.wait_for(processar(...), timeout=WHATSAPP_TURNO_TIMEOUT_S)   💭 120 s de partida
   estourou → status "timeout" no payload.turn · a mensagem NÃO se perde (§8) ·
              o dono é avisado · ⛔ nunca um "não entendi" ao segurado

CHAT DO PAINEL (SSE, com streaming)
   ⛔ NÃO se põe `wait_for` em volta do `astream_events` (graph.py:2062). Um turno que está
   EMITINDO delta não está travado — cortá-lo é regressão da SPEC-096, que entregou esse
   streaming. O relógio certo é TEMPO SEM PROGRESSO: nenhum delta por N s → encerra com
   `status="timeout"`. O heartbeat de 15 s (chat.py:398) fica: é para o proxy, não é teto.
```

🔴 Um teto total corta a resposta longa e boa; um teto de silêncio corta só o que está morto.

### 7.3 Retry com backoff — só no que é transitório

```
TRANSITÓRIO  → tenta de novo:  timeout · erro de conexão · HTTP 429 · HTTP 5xx
⛔ NUNCA      → falha na hora:  400 · 401 · 403 · 404 · chave inválida · modelo inexistente
backoff: full jitter — espera = random(0, base·2ⁿ), base 2 s, teto 30 s, no máximo 2 voltas
```

⚠️ Repetir um 401 queima a cota da corretora e atrasa todo mundo — é o mesmo raciocínio que a 001.6 §B3.2 escreveu para credencial de portal recusada. **Mesmo princípio, assunto diferente, código diferente: reaproveita-se a lição, não a função.**

### 7.4 Circuit breaker POR PROVEDOR

```
chave Redis:  llm_breaker:{provedor}        (openai · anthropic · google · openrouter)
estados:      fechado → aberto → meio-aberto      (§17 E1)
abre:         N falhas não-transitórias seguidas, ou N timeouts numa janela (💭 5 em 60 s)
meio-aberto:  depois de T (💭 120 s), deixa passar UMA chamada
```

🔴 **Por provedor, não por corretora, e a razão é o isolamento:** a Anthropic cair é fato do mundo, não da Resulta. Um breaker por corretora abriria N vezes para o mesmo fato, e cada corretora pagaria N timeouts para descobrir sozinha o que a primeira já sabia.

⛔ **Não duplicar o breaker de PORTAIS da EXTRA-001.6 §B3.3.** Aquele é por conta de portal (`portal_accounts.health`), tem o *"half-open é o gesto humano"* (salvar a senha nova) e vive no `portal-worker`. Este é por provedor de LLM, vive no `smith-api` e volta por timer. **Se a 001.6 tiver deixado um helper genérico, o executor o REUSA e diz onde**; se não, escreve o mínimo aqui e registra a consolidação como pendência.

🔴 **Breaker aberto não vira silêncio.** Aberto → a mensagem é **retida** (§8), o dono recebe frase humana 💭 *"o provedor de inteligência está fora do ar há 3 minutos; as conversas estão guardadas e vão ser respondidas assim que voltar"*, e **nada** chega ao segurado. Um breaker que faz o agente calar sem avisar é pior que timeout.

### 7.5 As ferramentas também

📊 **Já tem teto:** InfoCap 8–15 s (`infocap_connector.py:175, :1459, :1460, :4416`), Evolution 20–30 s (`evolution_go.py:346, :443, :454`), visão 30 s (`attendance_media.py:32`), subagente 30 s (`subagent_tool.py:36`). 📊 **Não tem:** 4 clientes `httpx.AsyncClient()` sem timeout algum (`mcp_servers/base_server.py:75`, `mcp_servers/google_drive_server.py:208`, `mcp_oauth_service.py:251` e `:384`) e as chamadas ao Supabase.

**Contrato:** teto default para todo `httpx.AsyncClient` criado no backend, e um guarda que **conta zero** clientes sem `timeout` (G6). ⚠️ Os 4 achados estão fora do caminho do atendimento; entram porque são 4 linhas e porque o guarda só consegue ficar vermelho se a regra valer para todos.

**GATE C.** ① os 4 construtores recebem `timeout` e `max_retries` (teste que lê os kwargs reais, não o fonte); ② `wait_for` no atendimento e **nenhum** `wait_for` total em volta do `astream_events`; ③ backoff com jitter: duas chamadas com o mesmo `n` dão valores diferentes; ④ 401 não entra no backoff; ⑤ breaker abre na 5ª e a 6ª chamada não sai; ⑥ zero `httpx.AsyncClient()` sem timeout.
**MUTAÇÃO C.** (a) tirar `timeout` de um construtor → ① vermelho; (b) aplicar backoff ao 401 → ④ vermelho; (c) breaker sem meio-aberto (nunca fecha) → uma chamada depois de T falha → ⑤ vermelho.

---

## 8. BLOCO D — contrapressão: a mensagem espera, nunca se perde

### 8.1 🔴 O defeito que a contrapressão descobre: o buffer EXPIRA

```
message_buffer_service.py:127   await self.redis.setex(key, settings.BUFFER_TTL_SECONDS, ...)
core/config.py:75               BUFFER_TTL_SECONDS: int = 60
```

📊 **O TTL do buffer é 60 s, contado desde a última escrita.** Com a fila andando em 1 s, é rede de segurança. Com a cota cheia e 50 conversas na frente, **uma conversa pode esperar mais de 60 s — e o Redis apaga o buffer.** O segurado escreveu, o webhook respondeu `{"status":"buffered"}`, e a mensagem sumiu **sem uma linha em lugar nenhum**. Não é consequência da cota: já é verdade hoje, e a cota o torna alcançável.

```python
async def adiar(self, chave: str, *, motivo: str) -> None:
    """Renova o TTL do buffer (EXPIRE) e incrementa o contador de espera do escopo.
    ⛔ NÃO reescreve o conteúdo (não mexe em `last_at`: isso remataria o debounce e a rajada
    nunca fecharia). Só o relógio de VIDA da chave, nunca o de PRONTIDÃO."""
```

Chamado sempre que uma chave pronta **não** é servida: cota cheia · turno tomado (001.2) · breaker aberto · escopo vazio. `motivo` é uma das quatro palavras, e vai para o contador e para o feed.

### 8.2 A conta que fecha — entrada = saída + retidas

```python
{"vistas": int, "prontas": int, "processadas": int,
 "adiadas": {"cota": int, "turno": int, "breaker": int, "sem_escopo": int},
 "falhas": int, "timeouts": int, "expiradas": int}
```

🔴 **`expiradas` tem de ser ZERO, e o guarda G7 o afirma.** É o único número desta SPEC que não admite "quase": uma chave que estava pronta numa varredura e não existe na seguinte, sem ter sido processada, é uma mensagem de segurado perdida.

### 8.3 O "digitando…" e o aviso ao dono

- **Presença "digitando…"**: o contrato é da **EXTRA-001.2 §6.4** (`sendPresence`, `presence ∈ {composing, paused, …}`). ⛔ Não reimplementar. Esta SPEC só acrescenta o gatilho: conversa **adiada por cota** liga a presença. Se a 001.2 não estiver na `main`, o gatilho fica escrito e desligado, e vira pendência nominal.
- **Aviso ao dono**: corretora acima da cota por mais de N s (💭 60) gera **um** aviso ao destino de suporte dela, pelo caminho que a **EXTRA-001.3** governa, com a mesma guarda de "humano já está nesta conversa" e **um** aviso por janela — nunca de 10 em 10 minutos, que foi como o grupo virou ruído (DIAGNÓSTICO §1.5). ⛔ Nenhum destino novo, nenhum canal novo.
- 💭 Copy ilustrativa, nunca citável: *"estamos com 12 conversas ao mesmo tempo aqui na Resulta e 4 estão esperando a vez. Ninguém foi perdido — vão sendo respondidas por ordem de chegada."*

**GATE D.** ① 200 chaves de uma corretora, cota 4, processador de 2 s: **zero** `expiradas` e entrada = processadas + adiadas; ② `adiar` renova o TTL e **não** altera `last_at` (duas leituras do JSON); ③ o aviso ao dono sai **uma vez** por janela, não por varredura.
**MUTAÇÃO D.** (a) `adiar` vira `pass` → ① **vermelho** com `expiradas > 0`; (b) `adiar` reescreve o buffer inteiro → ② **vermelho** (a rajada nunca fecha); (c) tirar a janela do aviso → ③ **vermelho** com N avisos.

---

## 9. BLOCO E — processos, réplicas e o lock de líder

### 9.1 A verdade desconfortável primeiro

🔴 **Mais processos aumentam o TETO. Cota e rodízio produzem o ISOLAMENTO.** O que a D-PILOTO-07 pede é isolamento — e B, C e D o entregam **num processo só**. Este bloco existe para (a) impedir que uma réplica acidental **duplique** os 24 jobs, e (b) deixar o caminho pronto e nomeado para o Founder subir capacidade.

| opção | nota | por quê |
|---|---|---|
| **lock de líder + `SCHEDULER_ENABLED`, mantendo 1 processo** | **88** | fecha o risco real (réplica dupla avisando duas vezes o mesmo grupo), custa zero mudança de deploy, e é **pré-requisito** das outras duas. Entra nesta SPEC |
| serviço `smith-jobs` separado (mesma imagem, comando próprio), API com o agendador desligado | 84 | é o alvo certo e tem precedente no repo (o `portal-worker` já é assim). Depende de 🧑 criar o serviço. Fica **preparado e desligado** |
| `uvicorn --workers N` | 41 | quebra o que é memória de processo: 📊 **P-096-STOP-MULTIPROCESSO** (`PENDENCIAS.md:10255`) — `TURNOS_ATIVOS` vive na memória e o `POST /chat/stop` cairia noutro worker → 404. Não entra sem consertar aquilo |

### 9.2 O lock de líder — no padrão que o repositório já usa

```python
# backend/app/tasks/buffer_processor.py, antes de scheduler.start()
CHAVE = "autobrokers:scheduler:lider"     # TTL 60 s, renovado a cada 20 s
token = uuid4().hex                        # E3: "a non-guessable large random string"
SET autobrokers:scheduler:lider {token} NX EX 60
EVAL <script literal da doc do Redis>      # renova/solta só se o valor ainda for o token
```

O script de soltura é o **literal da documentação** (§17 E3), o mesmo que `portal_worker/leases.py:130-145` já roda. ⛔ **Nunca `DEL` cego.**

```
não é líder      →  NÃO inicia o agendador; `/health` diz `scheduler: "seguidor"`
perdeu o lock    →  PARA o agendador e volta a tentar adquirir
Redis fora       →  🔴 FAIL-CLOSED para os jobs que ENVIAM (watchdogs, follow-up, cobrança);
                    fail-open só para os que leem/higienizam. A lista job a job vai na SPEC, e
                    o guarda G8 a verifica.
```

⚠️ Fail-closed aqui é o oposto do que `minio_backup.py:295-297` faz hoje (segue sem Redis). Está certo lá — backup duplicado não machuca. Está errado para o `handoff_watchdog`: dois avisos ao mesmo grupo é o ruído que a 001.3 existe para matar.

### 9.3 O poço de threads deixa de ser implícito

```python
# backend/app/main.py, no lifespan, ANTES de start_buffer_scheduler()
loop.set_default_executor(ThreadPoolExecutor(
    max_workers=int(os.getenv("EXECUTOR_THREADS", "0")) or min(32, (os.cpu_count() or 1) + 4),
    thread_name_prefix="to_thread"))
```

🔴 O default de hoje depende do `cpu_count` do contêiner e **ninguém o conhece** (BLOCO 0 item 9). Num contêiner de 1 vCPU são **5 threads** para 306 pontos de `to_thread` — e por elas passam quase todas as leituras ao Supabase de **todas** as corretoras. Tornar o número explícito e nomeado é o mínimo, e é literalmente o que o Bulkhead manda (§17 E1: *"consider using processes, thread pools, and semaphores"*).

⚠️ **Um executor por caminho (bulkhead completo) fica FORA** — mudaria 306 chamadas. §18, com gatilho.

### 9.4 O que o Founder muda no EasyPanel

| serviço | o que muda | quando |
|---|---|---|
| **smith-api** | variáveis novas: `WHATSAPP_COTA_POR_CORRETORA` · `WHATSAPP_TURNO_TIMEOUT_S` · `LLM_TIMEOUT_SEGUNDOS` · `LLM_MAX_RETRIES` · `LLM_BREAKER_FALHAS` · `LLM_BREAKER_SEGUNDOS` · `EXECUTOR_THREADS` · `SCHEDULER_ENABLED` · `ISOLAMENTO_ATRASO_ALLOWLIST` (vazia em produção) | nesta SPEC |
| **smith-api** | réplicas: continua **1** | nesta SPEC |
| **smith-jobs** (novo, opcional) | mesma imagem; comando `python -m app.tasks.jobs_runner`; `SCHEDULER_ENABLED=true`; 1 réplica. A API passa a `SCHEDULER_ENABLED=false` | 🧑 depois desta SPEC |
| **portal-worker** | nada | — |

⛔ **Nenhum valor de variável nesta proposta nem no relatório. Só o NOME.**

**GATE E.** ① dois processos do mesmo código: **um só** inicia o agendador, o outro diz `seguidor` no `/health`; ② matar o líder → o seguidor assume em ≤ TTL; ③ Redis fora → nenhum job de envio roda; ④ `EXECUTOR_THREADS` é lido e o executor default tem o tamanho pedido.
**MUTAÇÃO E.** (a) soltar o lock com `DEL` cego → um teste com dois donos fica **vermelho**; (b) fail-open no `handoff_watchdog` → ③ **vermelho**.

---

## 10. BLOCO F — a Central de Agentes passa a ver por corretora

📊 Hoje a Central responde *"o agente X produziu?"*, nunca *"a corretora Y foi atendida em quanto tempo?"*: `backend/app/core/central_de_agentes.py` calcula 5 estados por **grupo de agentes** (🟢 SAUDAVEL · 🟡 PULSA_SEM_PRODUZIR · ⚪ DESLIGADO · 🔴 PARADO · ⚫ NAO_MEDIDO), com cache Redis de 60 s, e a linha 29 declara *"⛔ Zero migration, zero tabela nova"*. **Esta SPEC respeita a declaração.**

Um bloco novo no MESMO JSON de `GET /api/admin/spec034/agents-status`:

```json
"atendimento_por_corretora": [
  {"company_id": "…", "nome": "…", "em_execucao": 2, "em_espera": 5, "cota": 4,
   "p95_ms_24h": 9400, "mediana_ms_24h": 5100, "ultimo_motivo_de_espera": "cota",
   "expiradas_24h": 0, "breaker": {"anthropic": "fechado"}}
]
```

Fontes, todas existentes: `em_execucao`/`em_espera` dos contadores Redis do §8.2; `p95`/`mediana` de `messages.payload.turn.total_ms` (§5.1) cruzado com `conversations.company_id`; `expiradas_24h` do contador; `breaker` da chave do §7.4. Frontend: `app/admin/central-agentes/page.tsx:640` já consome o endpoint — **uma seção nova na página que existe**, sem tela nova. ⛔ Nada de conteúdo de conversa atravessa: só contagens, estados, ids e tempos.

⚠️ **`expiradas_24h` é o número que o Founder deve olhar todo dia.** Responde sozinho à pergunta que hoje não tem resposta: *"perdi alguma mensagem?"*.

**GATE F.** ① o bloco aparece com dois `company_id` distintos e os números batem com os contadores; ② a rota continua `require_master_admin` e nenhum `company_id` alheio vaza; ③ `next start` + uma requisição a `/api/admin/spec034/agents-status` responde 200 (CLAUDE.md §9.1).
**MUTAÇÃO F.** remover o filtro de tenant da consulta de p95 → ① **vermelho** (os números das duas corretoras se fundem).

---

## 11. BLOCO G — a prova: duas corretoras, uma travada de propósito

### 11.1 Ordem canônica dos tenants

**Amandus → Resulta → AutoFleet** (CLAUDE.md §12). Para esta SPEC a exigência é mais forte: **duas corretoras ao mesmo tempo**, TESTE-A numa e TESTE-B na outra.

### 11.2 O atraso injetado — o único mecanismo novo que degrada de propósito

```python
def _atraso_de_teste_ms(company_id: str) -> int:
    """💭 Só para a prova de isolamento. FAIL-CLOSED por construção: lista vazia = ninguém
    (o desenho de JANELA_SILENCIO_EXCECOES, commit 05f46a9). Fora da allowlist → 0, não dorme."""
    permitidas = {c.strip() for c in os.getenv("ISOLAMENTO_ATRASO_ALLOWLIST", "").split(",") if c.strip()}
    if company_id not in permitidas:
        return 0
    return _env_int("ISOLAMENTO_ATRASO_MS", 0, minimum=0)
```

⛔ Em produção a variável fica vazia, e **G10 exige que o default produza ZERO atraso** — é o guarda que impede este mecanismo de virar defeito.

### 11.3 Os casos mínimos do canário

| # | o quê | o que prova |
|---|---|---|
| 1 | **antes**: TESTE-A na corretora 1 manda 3 mensagens; medir `total_ms` | a linha de base, sem doente |
| 2 | **durante**: corretora 2 com `ISOLAMENTO_ATRASO_MS` alto + rajada sintética de 20 conversas de teste; **ao mesmo tempo**, TESTE-A na corretora 1 manda 3 mensagens | 🔴 **o gate**: `total_ms` do caso 2 ≤ caso 1 + X (§5.4) |
| 3 | TESTE-B na corretora 2 (a doente) manda 1 mensagem | ele é atendido — **lento, mas atendido**; o `payload.turn` diz `adiado`/`cota`, não `failed` |
| 4 | rajada de 50 mensagens de TESTE-B em 30 s | entrada = saída + retidas; `expiradas` = **0** |
| 5 | breaker aberto na corretora 2 (provedor apontado para host inválido) | a corretora 1 **não sente**; o dono da 2 recebe **um** aviso; nada chega ao segurado |
| 6 | **depois**: allowlist esvaziada; repetir o caso 1 | o produto voltou ao normal, e a prova é o mesmo número do caso 1 |

🧑 **Só o Founder:** parear TESTE-A e TESTE-B em duas corretoras de teste distintas; ligar/desligar as variáveis do canário; clicar Implantar.

**GATE G.** os seis casos com saída real colada no relatório, por alias, e o número do caso 2 comparado ao do caso 1 pelo X do BLOCO 0.
**MUTAÇÃO G.** rodar o caso 2 com a cota desligada → o gate fica **vermelho** e o relatório mostra os dois números. 🔴 **Obrigatória: é a única prova de que o gate consegue ficar vermelho.**

---

## 12. Guardas e mutações — 10 novos, teto 12 (D-PILOTO-14)

Todos sobre o **MOTOR** e sobre o **ACERVO real** (CLAUDE.md §9.4). ⛔ Proibido teste que reimplementa a regra: um teste que recalcula o rodízio em vez de chamar `ordenar_em_rodizio` prova outra coisa.

| # | guarda | a mutação que o deixa VERMELHO |
|---|---|---|
| **G1** | `prontas()` e `should_process()` concordam sobre 20 buffers do corpus | `prontas` com régua própria |
| **G2** | `ordenar_em_rodizio` intercala e é **determinística** entre execuções | devolver a ordem do SCAN |
| **G3** | 50 chaves de A + 4 de B → as 4 de B terminam dentro de X, **com linha de controle** (a mesma rodada sem A) | `cota_por_corretora` altíssima |
| **G4** | a cota é adquirida **antes** do teto global (dois contadores de ocupação) | inverter a ordem |
| **G5** | o teste de paralelismo existente continua verde (`test_midia_e_concorrencia_do_webhook.py:519`) | chave da cota sem o escopo |
| **G6** | os 4 construtores recebem `timeout` e `max_retries`; zero `httpx.AsyncClient()` sem timeout | tirar `timeout` de um construtor |
| **G7** | 🔴 200 chaves, cota 4: `expiradas == 0` e entrada = processadas + adiadas | `adiar` vira `pass` |
| **G8** | não-líder não inicia o agendador; Redis fora → nenhum job de **envio** roda | fail-open no `handoff_watchdog` |
| **G9** | 401 não entra no backoff; breaker abre na 5ª e fecha depois de T | aplicar backoff ao 401 |
| **G10** | 🔴 sem `ISOLAMENTO_ATRASO_ALLOWLIST`, o atraso é **ZERO** para qualquer `company_id` | default virar "todos" |

⚠️ **G3, G5 e G10 não se negociam:** G3 é o outcome, G5 é a linha de controle herdada da 001.2, G10 é a trava do mecanismo perigoso desta SPEC.

⚠️ Mutação roda em **worktree próprio ou com lock exclusivo**, restaura por **CÓPIA**, nunca `git checkout` (protocolo §10). A bateria inteira **não** roda enquanto um juiz muta.

---

## 13. Migrations

📊 **Nenhuma migration prevista.** Tudo cabe onde já há lugar: o turno do atendimento em `messages.payload` (jsonb; o chat já grava `turn` ali) · contadores, lock de líder e breaker em Redis (trânsito, CLAUDE.md §6) · a Central no JSON do endpoint existente.

🔴 Se o executor concluir que precisa de SQL: lê `docs/canon/MIGRATIONS-AUTHORITY.md` **antes**, escreve **APPLY / VERIFY / ROLLBACK** antes de rodar, e registra em `CHANGE-ADDENDA.md`. ⚠️ Índice e GRANT disparam o piso CRÍTICO (protocolo §3.2) — só o COMMENT é isento.

---

## 14. Canário controlado em produção

### 14.1 Antes

Confirmar TESTE-A e TESTE-B, cada um na **sua** corretora de teste; conferir o remetente real sem tocar QR operacional; fixar janela e orçamento; provar os bloqueios com saídas simuladas **antes** de qualquer envio vivo.

🔴 **Os dois números na mesma corretora → o canário não prova isolamento.** O executor registra **PARCIAL com nome**; ⛔ nunca converte em verde e ⛔ nunca liga corretora operacional "só para medir".

### 14.2 Durante

Os seis casos da §11.3, nesta ordem, com o antes e o depois. Nenhum envio fora da allowlist, inclusive por alerta, fila, reenvio e resposta automática.

### 14.3 Depois

Esvaziar `ISOLAMENTO_ATRASO_ALLOWLIST`; conferir que nenhuma intenção do canário ficou pendente; repetir o caso 1 e mostrar que o número voltou; preservar logs sem PII; entregar evidências com aliases.

### 14.4 Validação com Saionara e Regina

Esta SPEC **não muda o que elas veem**, exceto pelo aviso do §8.3 e pelo bloco da Central. O que se valida é só isso: a frase do aviso soa humana? o bloco por corretora responde *"perdi alguma mensagem?"* sem explicação? O Founder conduz; o executor não as contata.

---

## 15. Entrega, implantação e rollback

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR. (CLAUDE.md §2)
git rev-list --count origin/main..HEAD
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do push, colada no relatório. Commit **arquivo por arquivo** — ⛔ nunca `git add -A`.

```
ORDEM DE IMPLANTAÇÃO:  smith-api  →  smith-web       (o portal-worker não muda)
ROLLBACK, em 3 variáveis:
   WHATSAPP_COTA_POR_CORRETORA = número muito alto  → a cota deixa de morder
   LLM_TIMEOUT_SEGUNDOS = 0                          → volta o comportamento do SDK
   SCHEDULER_ENABLED = true em todas as réplicas     → volta o comportamento de hoje
🔴 Reverter código não desfaz mensagem enviada. Preservar evidência e impedir repetição.
```

⚠️ Mexeu em `app/` do frontend: `npm run test:rotas-montam` + `next start` + **uma requisição a `/api/…`** antes de declarar gate verde (CLAUDE.md §9.1).

| marco | evidência exigida |
|---|---|
| implementado e gateado | commit, G1–G10 verdes, as 10 mutações vermelhas com o nome da falha nova |
| entregue na `main` | SHA remoto e a saída do `git push` |
| implantado | serviço/imagem/SHA + `/health` com `scheduler: "lider"` |
| validado no canário | os 6 casos da §11.3, por alias, com os números lado a lado |
| ativado em corretora operacional | 🧑 fora da autorização desta execução |

---

## 16. Documentação e acompanhamento obrigatórios

1. **Relatório** em `docs/canon/reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md`, pelo template, **abrindo com o EXECUTION CARD**, com a telemetria de 5 linhas (protocolo §11).
2. **`PENDENCIAS.md`** — re-julgar **por número**, com prova (`FECHADA` · `CONTINUA` com o que destrava · `MORREU`): **P-PILOTO-01** (a origem) · **P-096-STOP-MULTIPROCESSO** (`:10255`) · **P-237** (`:8167`, load→mutate→save sem lock) · **P-238** (`:8183`, o Vigia morre sem Redis) · **P-207** (`:5594`, o freio significa coisas opostas em dois processos) · **P-248** (`:8774`, `/health` não expõe o Smith Worker).
3. **`ESTADO-DAS-SPECS.md`** e **`EXECUTION-MASTER-PLAN.md`**.
4. **`CHANGE-ADDENDA.md`** — tudo além do texto da SPEC, classificado BLOCKER · ESSENCIAL · VALIOSA · FUTURA, **antes** de executar.
5. **`FOUNDER-DECISIONS.md`** — só se nascer decisão nova (💭 candidata: o X do §5.4 vira o primeiro SLO declarado do projeto).
6. **Dossiê:** https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 — ler o HTML publicado **inteiro** antes de republicar com a mesma `url`; aba **Pilotos**. Sem acesso: atualizar `docs/canon/reports/dossies/dossies-autobrokers.html` e dizer **"publicação pendente"** com o passo exato. ⛔ Nunca alegar que o link foi atualizado.

---

## 17. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> 🔴 O pesquisador (protocolo §7.3) **reabre** as três e escreve a data na SPEC definitiva. Abaixo, a leitura de **13/09/2026**.

### E1 — Microsoft · Bulkhead pattern
**URL:** https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead · reaberta 13/09/2026
**Faz:** particiona recursos por consumidor para que a falha de um não se propague. Nomeia o nosso elo ④: *"the client's connection pool might be exhausted. At that point, the consumer's requests to other services are affected"*, e *"Many requests from one client might exhaust available resources in the service… which causes a cascading failure effect"*. Para partir consumidores recomenda *"processes, thread pools, and semaphores"*, e diz que bulkhead se combina com *"retry, circuit breaker, and throttling patterns"*.
**MODELAMOS:** ① **semáforo por consumidor** = a cota por corretora do §6, com o consumidor sendo o `escopo` da chave do buffer; ② **thread pool dimensionado** = `EXECUTOR_THREADS` do §9.3 — a partição que o documento manda fazer primeiro e que hoje não existe.
**REJEITAMOS:** *"deploying them into separate virtual machines, containers, or processes"* como forma **desta** SPEC. Um contêiner por corretora é a granularidade que o próprio texto manda escolher com cuidado (*"determine the level of granularity"*) e que, com duas corretoras piloto, custa mais do que entrega. §18, com gatilho.
**Como o juiz inspeciona:** abre a página, confere que "Problems and considerations" cita semáforos e thread pools, e compara com `cota_de()` e `set_default_executor` no diff.

### E2 — Kubernetes · API Priority and Fairness
**URL:** https://kubernetes.io/docs/concepts/cluster-administration/flow-control/ · reaberta 13/09/2026
**Faz:** é a implementação de referência de **cota + fila justa** num sistema multi-inquilino real. O limite global de concorrência é *"divided up among a configurable set of priority levels"*, e cada nível *"will only dispatch as many concurrent requests as its particular limit allows"*; dentro do nível, *"a fair-queuing algorithm prevents requests from different flows from starving each other"*. O objetivo declarado é o nosso, palavra por palavra: *"a poorly-behaved [controller] need not starve others"*.
**MODELAMOS:** ① **teto global repartido em cotas** — é o §6.3 (cota da corretora dentro do teto do processo), e é a razão de o "pool por corretora sem teto global" valer 62; ② *"introduces a limited amount of queuing, so that no requests are rejected in cases of very brief bursts"* → o §8: a rajada **espera**, não é recusada nem perdida.
**REJEITAMOS:** ① **borrowing** (nível ocioso emprestar concorrência ao saturado) — com 2 corretoras não paga, e emprestar é a porta pela qual a interferência volta; ② **shuffle sharding** — resolve *quem divide fila com quem* quando há mais inquilinos que filas; a nossa cota é nominal por `escopo` e não precisa de sorteio.
**Como o juiz inspeciona:** abre a página, lê "Concepts", e confere que a nossa cota é subdivisão de um teto (e não um teto novo por corretora) lendo a ordem de aquisição em `_uma`.

### E3 — Redis · `SET` (NX/EX) e o script de soltura
**URL:** https://redis.io/docs/latest/commands/set/ · reaberta 13/09/2026
**Faz:** documenta que `SET resource-name anystring NX EX max-lock-time` *"is a simple way to implement a locking system with Redis"*, e prescreve as duas correções que o tornam honesto: *"Instead of setting a fixed string, set a non-guessable large random string, called token"* e *"Instead of releasing the lock with DEL, send a script that only removes the key if the value matches"* —
```lua
if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) else return 0 end
```
**MODELAMOS:** o **lock de líder do agendador** (§9.2): token aleatório, `EX 60`, renovação a cada 20 s, soltura pelo script literal. É o padrão que `portal_worker/leases.py:130-145, :421` já roda em produção — reaproveitamos a forma, não copiamos o arquivo (aquele é lease por conta de portal).
**REJEITAMOS:** ① **Redlock** (que a própria página recomenda por cima do `SET NX`): temos **um** Redis, não N independentes; Redlock sem N mestres é cerimônia sem garantia. ② **Redis Streams com consumer group** para o atendimento — lida (https://redis.io/docs/latest/develop/data-types/streams/, mesma data) e **rejeitada de propósito**: o padrão já existe no repo (`app/services/work/queue.py:26-116`, com `xreadgroup`/`xautoclaim`/`xack`) e serve Work Runs; trazê-lo para o WhatsApp criaria uma segunda fila sobre a mesma mensagem — o motor paralelo do CLAUDE.md §5. O buffer **já é** a fila e o `GET+DEL` em pipeline **já é** a entrega única.
**Como o juiz inspeciona:** abre "Patterns" na página, compara o Lua do diff caractere a caractere com o da doc, e confirma que não há `DEL` cego no caminho de soltura.

---

## 18. O QUE SAIU, E QUANDO VOLTA

| frente | por que não entra agora | gatilho de retorno |
|---|---|---|
| **executor de threads por caminho** (bulkhead completo) | mudaria 306 chamadas de `to_thread`; o ganho é desconhecido antes de medir | o BLOCO 0 mostrar o poço saturado sob a carga do §5.3 |
| **rate limit por corretora na ENTRADA do webhook** (hoje por IP: `webhook.py:1387`, `rate_limit.py:28`) | a entrada não é o gargalo medido; e o IP é do provedor, então a chave certa é o `escopo`, só conhecido depois do auth | uma corretora estourar o balde e calar as outras |
| **`uvicorn --workers N` / réplicas da API** | 📊 P-096-STOP-MULTIPROCESSO: `TURNOS_ATIVOS` é memória de processo e o `/chat/stop` cairia noutro worker | fechar P-096-STOP-MULTIPROCESSO |
| **serviço `smith-jobs` separado** | depende de 🧑 criar o serviço no EasyPanel | o Founder criar o serviço; o código já sai pronto (§9.4) |
| **borrowing entre corretoras** (E2) | com 2 corretoras não paga, e é por onde a interferência volta | dezenas de corretoras com carga desigual medida |
| **Prometheus / OpenTelemetry** | 📊 zero instrumentação hoje (`grep -rni "prometheus\|opentelemetry\|statsd" backend/app` → 2, ambos comentário bibliográfico); a Central resolve o que esta SPEC precisa | uma SPEC que precise de série temporal, não de instantâneo |
| **pool de banco por corretora** | o Supabase é acessado por service role com pool único; partir isso é SPEC própria | saturação de conexões medida |
| **breaker de portal** | é da **EXTRA-001.6 §B3.3**, já escrita | — (não volta; só se referencia) |

🔴 **Nada da §2.1 sai em silêncio.** Conflito material vira proposta em `CHANGE-ADDENDA.md` — recorte unilateral não se chama "otimização AAA" (CLAUDE.md §11).

---

## 19. Fila depois desta entrega

Ordem canônica (DIAGNÓSTICO §12.1): `001.0 → 001.6-P0 → 001.1 → 001.2 → 001.3 → 001.4 → 001.6 → 001.7 → 001.10 → 001.5 → **001.8 (esta)** → 001.9`.

| para quem | o que esta SPEC deixa pronto |
|---|---|
| **001.7** (piloto medido) | 🔴 o `payload.turn` do atendimento e o p95 por corretora — a régua que a 001.7 precisa e que hoje não existe |
| **001.9** e a SPEC de painel | a seção por corretora da Central, onde as métricas de operação passam a morar |
| **SPEC-101 / EXTRA-002/008/009** | a cota por `escopo` vale para qualquer adaptador: um conector lento de uma corretora não trava a outra |
| qualquer SPEC com job periódico | o lock de líder, que deixa de ser decisão de cada job |

⚠️ **A 001.8 vem depois da 001.2, não antes** (§3.3). E vir depois da 001.7 seria pior: sem o `payload.turn` do atendimento, a 001.7 mediria a operação com régua emprestada do chat.

---

## 20. DEFINIÇÃO FINAL DE CONCLUSÃO — lista fechada e verificável

```
[ ]  1. EXECUTION CARD no topo do relatório, com o X do §5.4 preenchido e o comando ao lado
[ ]  2. BLOCO 0: as 16 premissas remedidas, com comando e valor de hoje — inclusive o item 9
        (cpu_count/threads DENTRO do smith-api implantado)
[ ]  3. G1–G10 verdes, e as 10 mutações VERMELHAS, cada uma com o nome da falha nova em subprocesso
[ ]  4. o teste de paralelismo que já existe (test_midia_e_concorrencia_do_webhook.py:519)
        continua VERDE — a linha de controle herdada da 001.2
[ ]  5. `expiradas == 0` sob a carga do §5.3 e no caso 4 do canário
[ ]  6. canário: os 6 casos da §11.3, com TESTE-A e TESTE-B em CORRETORAS DIFERENTES, e o número
        do caso 2 comparado ao do caso 1 — ou o PARCIAL nomeado da §14.1
[ ]  7. `ISOLAMENTO_ATRASO_ALLOWLIST` vazia no implantado, conferida DEPOIS do canário
[ ]  8. a suíte inteira, 2 a 4 vezes na SPEC, com a contagem no relatório
[ ]  9. `next start` + uma requisição a `/api/…` respondendo 200 (mexeu na Central)
[ ] 10. `git push origin HEAD:main` com a saída COLADA; `/health` do implantado com `scheduler`
[ ] 11. PENDENCIAS: as 6 da §16.2 re-julgadas com prova; pendências novas registradas
[ ] 12. dossiê republicado na MESMA url, ou "publicação pendente" com o passo exato
```

🔴 **Um item aberto = SPEC aberta.** "Quase tudo verde" não é um estado.

---

## 21. 📋 CAIXA DO FOUNDER

| # | o que é | o que custa esquecer | bloqueia? |
|---|---|---|---|
| 1 | **Parear TESTE-A e TESTE-B em duas corretoras de teste distintas** | sem isso o canário não prova isolamento, só latência | **SÓ o §14**; A–F seguem |
| 2 | Ligar e desligar `ISOLAMENTO_ATRASO_ALLOWLIST` no canário | é o único mecanismo que degrada de propósito | só o §11.3 |
| 3 | Definir as variáveis novas no smith-api (§9.4) e clicar **Implantar** | o código sobe com os defaults; funciona, mas não com o número medido | não |
| 4 | Decidir se cria o serviço `smith-jobs` | capacidade, não isolamento. O código já sai pronto | não |
| 5 | Aceitar o **X** do §5.4 como o primeiro SLO declarado do projeto | sem número, "nenhuma interferência" não é verificável | não — o executor escolhe e registra (protocolo §9) |

⛔ **Nunca parar para entregar uma linha desta caixa** (protocolo §9).

---

> **O resultado, em uma frase:** quatro segurados de cada corretora são atendidos ao mesmo tempo; a corretora com o modelo lento espera sozinha; e a pergunta *"perdi alguma mensagem hoje?"* passa a ter uma resposta, que é **zero**.
