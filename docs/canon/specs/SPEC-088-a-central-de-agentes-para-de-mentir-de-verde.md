# SPEC-088 · A CENTRAL DE AGENTES DIZ A VERDADE — e mostra o trabalho de cada trabalhador

> **O que ela entrega:** a Central deixa de responder *"o laço pulsou?"* e passa a
> responder *"o trabalho aconteceu?"* e *"quanto trabalho, com que resultado?"*. Cada
> trabalhador digital tem uma cor que sai de **duas** medições (pulso **e** produção na
> cadência dele), um grupo por propósito, e um painel com execuções, falhas, entregas,
> travamentos e aprovações lidos das tabelas reais. O motor de inteligência, hoje
> invisível, aparece.
>
> **v2 · 03/09/2026 · protocolo v11** · commit base `5e8792c` · repo `AutoBrokers-FIX`
> Proposta: `specs-propostas/4 - SPEC-088-central-de-agentes-organizacao-operacional.md`
> Research-pack: `specs-propostas/4 - SPEC-088-…-RESEARCH-PACK.md` · reaberto em 03/09/2026
> Insumo: a v1 desta SPEC (02/09), cujas medições foram reconferidas hoje e mantidas onde bateram.

---

## 0. O TESTE DO PRODUTO

> **A Sentinela morre numa quinta. Na sexta o Founder abre a Central e vê o card dela
> AMARELO com "pulsa há 6h, não destrava nada há 2 dias", dentro do grupo ATENDE
> AGORA, com a linha "2 de 3 saudáveis", e ao lado o Detector de sinais, que rodou
> 504 vezes na semana e hoje não aparece em lugar nenhum.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.

A Central é `require_master_admin` (📊 `backend/app/api/admin_spec034.py:28`): o
segurado nunca a vê. O que ela vigia é quem fala com ele. Um instrumento cego sobre a
cadeia de atendimento é o motivo de ninguém ter percebido 📊 **18 dias** de
`knowledge_cards` parado (`max(created_at)` = 16/08/2026 16:46, consulta em 03/09).

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU — 03/09/2026, produção `dcajcvlzcjbmyapmklil`

### 1.1 · A Central lê UMA fonte, e é a errada

```
backend/app/core/heartbeat.py:78-98   read_all() lê SÓ Redis (spec034:heartbeat:{task}, TTL 7 dias :18)
app/admin/central-agentes/page.tsx:36-42   health(): <900s 🟢 · <7200s 🟡 · senão 🔴 · null ⚪
backend/app/api/admin_spec034.py:27-31     a rota: 4 linhas, devolve read_all()
```
📊 `grep -rn "work_runs\|artifacts\|approval_requests\|usage_events" backend/app/api/admin_spec034.py` → **0**.
A Central não lê `work_runs`, `agents`, `tenant_auxiliaries`, `routines`, `artifacts`,
`approval_requests`. Nenhuma.

### 1.2 · O motor canônico é invisível

📊 `SELECT workflow_key, count(*) FROM work_runs WHERE created_at > now()-interval '7 days' GROUP BY 1`:

```
intelligence.detect_signals ............ 504     intelligence.garimpo ........ 21
intelligence.measure_outcomes ..........  84     intelligence.cluster_demand .  7
intelligence.daily_briefing ............  21     intelligence.weekly_executive_briefing  3
                                                                    total  640
```
📊 `grep -rn "beat(" backend/app/services/intelligence/ | wc -l` → **0**. 📊 Dos 14 ids de
`AGENT_TASKS` (`heartbeat.py:22-50`), **2** têm `workflow_key` correspondente (`garimpo`,
`auditor` parcial via `investigate_quality`) e **2** têm task dedicada em `app/tasks/`
(`vigia_sentinela`, `followup`). **Os outros 10 vivem só no Redis.**

### 1.3 · O pulso mede o laço, e o laço pode rodar sem produzir

📊 `intelligence.garimpo`: 21 execuções `completed` em 7 dias. `broker_insights`:
`max(created_at)` = **26/08/2026 00:05**, 270 linhas, todas `source='garimpo_v3'`.
`intelligence_signals` com `source_type='garimpo'`: 32 linhas, última 26/08 00:04.
**Oito dias de laço rodando e zero produção.** O card de hoje alterna 🟢/🟡 pela idade do
pulso e nunca fica vermelho por isso.

### 1.4 · O pulso que existe está morto em três lugares, não em um

O `cutover_ligado()` (`backend/app/services/intelligence/legacy_adapter.py:34-36`,
default `"1"` = ligado; 📊 o ambiente de produção não define `INTELLIGENCE_CUTOVER`)
retorna antes do `beat()` em **três** funções:

| pulso | o `return` que o impede | o `beat()` inalcançável |
|---|---|---|
| `garimpo` | `broker_insights.py:310-311` | `broker_insights.py:343` (dentro de um `finally` de OUTRO `try`, `:337`) |
| `sugestoes` | `proactive_suggestions.py:223-224` | `proactive_suggestions.py:232` — **e não há outro pulso para ele** |
| `auditor` | `regression_sentinel.py:123-124` | `regression_sentinel.py:160` (o `conversation_auditor.py:180` ainda pulsa, 1×/dia) |

⚠️ A v1 desta SPEC listava só o do Garimpo. Os dois outros foram medidos em 03/09 com
`grep -rn "cutover_ligado" backend/app/services/*.py` e leitura da linha 1 de cada função.

### 1.5 · Oito pulsos cruzados, e a casa do Alfaiate não pulsa

📊 `grep -rn "await beat(\|await _beat(" backend/app --include=*.py | wc -l` → **27 chamadas em 18 arquivos**.
Oito delas dão o pulso de OUTRO agente: `agent_memory.py:212`→espelho ·
`atlas/history_ingest.py:204`→espelho_atendimento · `atlas/history_ingest.py:212`→observador ·
`atlas/route_sentinel.py:444`→alfaiate · `attendance_distiller.py:1344`→espelho_atendimento ·
`conversation_auditor.py:181`→alfaiate · `prompt_optimizer.py:199`→alfaiate ·
`regression_sentinel.py:160`→auditor. 📊 `grep -c "beat(" backend/app/services/playbook_tailor.py` → **0**.

### 1.6 · A lista dupla envelheceu, e o vermelho do lento é por desenho

📊 `page.tsx:16-20` `COLORS` tem **9** ids; `heartbeat.py` tem **14**. Sem cor: `observador`,
`tecelao`, `sentinela_rotas`, `espelho_atendimento`, `conselho`. E o limiar único de
900s condena quem roda 1×/dia (`conversation_auditor.py:143-144`, marcador diário) a
viver 🔴 e promove quem pulsa de hora em hora a 🟢.

### 1.7 · O que EXISTE para a visão por trabalhador — e o que não existe

```
📊 work_runs 30d ............ 2.679 · 100% com workflow_key, correlation_id, thread_id, cost_actual_brl
   requester_agent_id ....... 0 de 2.679     skill_release_id ... 0 de 2.679
   cost_actual_brl > 0 ...... 0 de 3.494 (toda a história)         ← o custo existe como coluna e vale zero
   falhas 30d ............... 0 em todos os 8 workflow_key         duração média 2,8s–9,9s (acionamento: 47h)
📊 artifacts 30d ............ 118 · 85 com work_run_id (72%)  — os órfãos vêm de 6 chamadores que não passam o id
📊 approval_requests pending  0 · work_waits .... 0 linhas · unblock_state='travado' .... 1
📊 usage_events 30d ......... 400 · 0 com work_run_id · correlation_id NÃO casa com work_runs (0 de 394)
   source: chat 199 · memory 193 · tool 6 · vision 2   ← é o custo do CHAT; os workflows não geram usage
📊 auxiliary_events ......... 0 (P-18: escritor existe em factory.py:460-471, ZERO chamadores)
📊 bridge.routine.execute ... 7 runs (a ponte já rodou) · bridge.auxiliary.execute ... 0
📊 índices em work_run_id ... usage_events ✓ · artifacts ✓ · approval_requests ✓
```

### 1.8 · O que mudou desde a v1 — e muda a narrativa

📊 `attendance_transcripts` e `conversations` voltaram a crescer em **03/09 01:39**, depois
que a API subiu (7 dias no chão, `4c8a718`). Parte do "silêncio de 7 dias" da v1 era a API
morta, não os agentes. ⚠️ **A Central não distinguiu uma coisa da outra. É o defeito.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado. NENHUM agente é ligado. NENHUM `is_active` muda.
⛔ NENHUMA entrada em portal. API InfoCap intocada.
⛔ Banco: SELECT livre. 🔴 ZERO migration nesta SPEC (§6). Sem tabela nova, sem coluna nova.
⛔ A Central continua `require_master_admin`. NADA daqui aparece para corretora.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa — nem na rota nova:
   ela devolve contagens, estados, ids e timestamps. Nunca texto de conversa.
⛔ NÃO mexer em variável de ambiente. NUNCA `git add -A`.
```

---

## 2.1 O EXECUTION CARD da conversão — o executor confere e discorda com número

```
OUTCOME ..............  a Central diz a verdade por trabalhador e mostra o trabalho dele
RISCO ................  4   ALCANCE 2 (tela admin; o que ela vigia alcança o segurado, cadeia de 2 passos)
                            REVERSIBILIDADE 0 (zero migration; revert + chaves Redis expiram = nada sobra)
                            FREQUÊNCIA 2 (beat() em todo atendimento; a rota é consultada a cada 20s)
SUPERFÍCIE ...........  2   vários comportamentos e uma peça nova (o leitor de produção). 🔴 Era 3 na v1;
                            desce porque o território FOI mapeado em 03/09: 27 call sites, 14 ids,
                            20 workflow_keys, 8 tabelas, com file:line (§1). Se o executor achar
                            call site fora da lista, volta a 3 e o nível sobe
PISO APLICADO ........  nenhum, por efeito: não envia · sem migration · não toca auth nem company_id
                            (a rota é de plataforma e agrega) · não escreve noutra corretora
NÍVEL ................  PADRÃO   (RISCO 2–5, SUPERFÍCIE 2)
UNIDADES .............  5   BLOCO A+B (backend: registro + estados) · BLOCO C (rota e leitor de trabalho) ·
                            BLOCO D (frontend) · BLOCO E (pulsos: os 3 mortos e os 8 cruzados) · BLOCO F (guarda)
COESÃO ...............  A+B+C juntas (mesmo módulo e mesma interface JSON) · D separada, contra o CONTRATO da §5 ·
                            E separada (só call sites de beat) · F separada (só testes). Arquivo-hub: heartbeat.py = um dono
PARALELISMO REAL .....  3 escritores: {A+B+C} · {D} · {E}. F começa junto, pelo contrato. Integração serial
TIME .................  investigador ✅ (03/09) · pesquisador ✅ (03/09) · 3 builders · verificador ·
                            painel de 3 lentes · juiz de confirmação
REFERÊNCIA ...........  interna: `backend/tests/test_o_protocolo_tem_policia.py` (forma do guarda) ·
                            `backend/tests/test_a_casa_diz_a_verdade.py` (tela contra código) · DS-001 §5
                            externa: §7.3 — Prometheus last_success · Dagster freshness/no_policy · Temporal worker-health
GATES ................  por bloco, abaixo. Todos com mutação
O ELO ................  "o card mente PORQUE mede o laço e não a produção": medido — 21 runs completed
                            × broker_insights parado em 26/08 × health() só lê last_run (§1.1, §1.3)
FAIXA DE RELÓGIO .....  🔴 5–8h de execução, com os três builders em paralelo
```

---

## 3. 🌐 O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS — §7.3, reaberto em 03/09/2026

As 13 referências do research-pack (§55) foram reabertas: 📊 **13 de 13 vivas**, nenhuma
404. Duas mudaram (`code.claude.com/docs/en/sub-agents` ganhou campos; `agent-teams`
reescreveu a API). ⚠️ **E o achado incômodo:** as 13 falam de *orquestrar* agentes;
nenhuma responde *"como sei que este trabalhador está produzindo?"*. O pack é de
runtime; esta SPEC é de saúde. As referências ① a ④ abaixo foram buscadas por isso.

### ① `last_success` separado de `last_run` — o defeito tem nome e cura publicada
```
URL ................. https://www.robustperception.io/monitoring-batch-jobs-in-python/  (03/09/2026)
o que ela faz ....... duas séries por job: uma marca a rodada; `last_success` é escrita SÓ no
                      ramo de sucesso, e o alerta é `time() - last_success > 3,5 × intervalo`
MODELAMOS ........... BLOCO A: `fonte_de_producao` É o last_success do agente; `beat()` é o last_run.
                      BLOCO B: o limiar é k × `cadencia_esperada` DELE, não 900s para todos
REJEITAMOS .......... Pushgateway como peça: segundo lugar para a verdade (CLAUDE.md §5). A produção
                      sai da tabela que o agente JÁ escreve
COMO O JUIZ INSPECIONA abre a página · compara o `else:` do exemplo com o `finally` de
                      `broker_insights.py:337`: o artigo grava sucesso NO ramo de sucesso; nosso pulso
                      nasce no `finally`. Confere que o limiar da tabela do BLOCO A é por agente
```
### ② Airflow removeu o alerta que só disparava quando a coisa rodava
```
URL ................. https://airflow.apache.org/docs/apache-airflow/stable/howto/sla-to-deadlines.html  (03/09/2026)
o que ela faz ....... "If the Dag run never finishes, the SLA is never checked." O `sla_miss_callback`
                      saiu no Airflow 3.0; o substituto ancora o prazo na CADÊNCIA, não no último evento
MODELAMOS ........... BLOCO B, estado 🔴 PARADO: ancorado na cadência esperada. Quem nunca produziu
                      (📊 `playbook_overlays` = 0 linhas) alerta — hoje não há evento para comparar
REJEITAMOS .......... o scheduler de 5s: 14 consultas × 12/min contra produção. Cache de 60s
COMO O JUIZ INSPECIONA abre "How they differ" · aplica à mutação 2 do BLOCO B (chave de heartbeat
                      expirada): se der ⚪ em vez de 🔴, é o bug que o Airflow removeu, vivo aqui
```
### ③ Dagster: cadência POR ativo, e "sem política" é um estado explícito
```
URL ................. https://docs.dagster.io/guides/observe/asset-freshness-policies
                      https://docs.dagster.io/examples/best-practices/asset-health-monitoring  (03/09/2026)
o que ela faz ....... cada ativo declara a própria freshness policy, medida sobre "a successful
                      materialization"; saúde agrega materialização · checks · frescor em
                      HEALTHY/WARNING/UNHEALTHY/DEGRADED; ativo sem política = `"no_policy"`, explícito
MODELAMOS ........... BLOCO A: `cadencia_esperada` por agente; `fonte_de_producao = None` → ⚫ NÃO MEDIDO
                      (o `no_policy` deles). BLOCO B: 🟡 PULSA SEM PRODUZIR é o par (rodou OK, frescor
                      falhou) que um enum de 3 estados não expressa
REJEITAMOS .......... duas faixas de warning por agente (dobra a configuração e nada disso é medido
                      hoje) · auto-materialize (é runtime; a Central não religa ninguém)
COMO O JUIZ INSPECIONA abre a 2ª URL, procura `no_policy` · confere `None` EXPLÍCITO nas linhas sem
                      fonte de `AGENT_TASKS` e que a mutação do BLOCO A pinta ⚫, nunca 🟢
```
### ④ Temporal: worker que faz poll NÃO é worker saudável — e o sintoma da nossa Central, num produto maduro
```
URL ................. https://docs.temporal.io/cloud/worker-health
                      https://community.temporal.io/t/schedule-stopped-working-but-showing-in-running-status/19759  (03/09/2026)
o que ela faz ....... saúde de worker = Schedule-To-Start latency, poll success, slots — nunca "está
                      conectado". A thread (10/08/2026): "all schedules showing running status but
                      that schedule is not running"
MODELAMOS ........... BLOCO B: 🟢 exige DUAS medições. BLOCO C: a visão por trabalhador traz a latência
                      `started_at - created_at` (📊 hoje 13s–100s por workflow) — fila parada com worker vivo
REJEITAMOS .......... task slots e sticky cache (métricas de um runtime que não é o Smith) · Grafana/OTLP
                      como destino (Control Plane paralelo)
COMO O JUIZ INSPECIONA abre a thread e a doc · confere que nenhum dos 4 sinais deles é "último pulso" ·
                      confere que a rota nova devolve `fila_media_s`
```
### ⑤ Claude Code agent teams: linha escondida ≠ agente parado
```
URL ................. https://code.claude.com/docs/en/agent-teams  (03/09/2026 — a API mudou desde 25/08)
o que ela faz ....... estado POR membro (working · idle · failed); "a teammate row that disappeared
                      after sitting idle has been hidden, not stopped"; acima de 3 ociosos, colapsa
MODELAMOS ........... BLOCO B: ausência de sinal NUNCA é o estado benigno — dúvida pinta 🔴, não ⚪.
                      BLOCO D: 4 grupos com resumo, nunca 14+ cards soltos
REJEITAMOS .......... mailbox e mensagens entre pares: peer teams adiados para a 088-B (pack §56)
COMO O JUIZ INSPECIONA abre "Teammates not appearing" · confere o gate ② do BLOCO B: `is_active=false`
                      em TODAS as corretoras → ⚪; qualquer dúvida → 🔴
```
### ⑥ Datadog Software Catalog: grupo e dono são METADADO da entidade, a UI só lê
```
URL ................. https://docs.datadoghq.com/internal_developer_portal/catalog/entity_model/  (03/09/2026)
o que ela faz ....... `kind`, `owner` e agrupamento vivem no schema versionado da entidade; sem dono
                      declarado aparece "sem dono", nunca adotado por default
MODELAMOS ........... BLOCO A: `grupo` e `cor` saem de `page.tsx` e vivem em `AGENT_TASKS`, a ÚNICA lista
                      (mata a §1.6). Gate: o frontend não tem lista de agente nenhuma
REJEITAMOS .......... `kind` técnico fixo: nossos grupos são por propósito para a corretora · o catálogo
                      como produto (Control Plane paralelo)
COMO O JUIZ INSPECIONA `grep -rn "observador\|garimpo\|alfaiate" app/admin/central-agentes/` → tem de dar 0
```
### ⑦ Anthropic multi-agent research: tracing de estrutura, nunca de conteúdo
```
URL ................. https://www.anthropic.com/engineering/multi-agent-research-system  (03/09/2026)
o que ela faz ....... "we monitor agent decision patterns and interaction structures — all without
                      monitoring the contents of individual conversations"
MODELAMOS ........... BLOCO C: a rota devolve contagens, estados, ids e timestamps de work_runs,
                      artifacts, approval_requests — nunca payload. É a trava de PII sem coluna nova
REJEITAMOS .......... rainbow deploy, checkpoint/resume, LLM-as-judge: runtime e Quality Health, fora
COMO O JUIZ INSPECIONA roda a rota contra um tenant real e confere no JSON que nenhum campo textual de
                      conversa atravessa
```

**O que o estado da arte faz que nós não fazemos, por valor** (nota do pesquisador):
separar last_success de last_run **98** · limiar por unidade **95** · "sem política" explícito
**92** · matar alerta que só dispara quando rodou **88** · ausência ≠ benigno **85** · grupo como
metadado **80** · saúde multidimensional **74** · tracing sem conteúdo **70** · latência fila→início **55**.

---

# BLOCO 0 · REMEDIR, antes da primeira linha

Os números desta SPEC são de 03/09/2026. Rode e cole no relatório:

```sql
-- ① o laço roda e a saída não cresce?
SELECT workflow_key, status, count(*), max(created_at) FROM work_runs
 WHERE created_at > now()-interval '7 days' GROUP BY 1,2 ORDER BY 3 DESC;
SELECT 'broker_insights' t, count(*), max(created_at) FROM broker_insights
UNION ALL SELECT 'intelligence_signals', count(*), max(greatest(last_seen_at, created_at)) FROM intelligence_signals
UNION ALL SELECT 'conversation_scorecards', count(*), max(created_at) FROM conversation_scorecards
UNION ALL SELECT 'observed_events', count(*), max(created_at) FROM observed_events
UNION ALL SELECT 'ura_maps', count(*), max(created_at) FROM ura_maps
UNION ALL SELECT 'route_drift', count(*), max(created_at) FROM route_drift
UNION ALL SELECT 'attendance_transcripts', count(*), max(created_at) FROM attendance_transcripts
UNION ALL SELECT 'playbook_overlays', count(*), max(created_at) FROM playbook_overlays
UNION ALL SELECT 'platform_sends', count(*), max(created_at) FROM platform_sends
UNION ALL SELECT 'knowledge_cards', count(*), max(created_at) FROM knowledge_cards
UNION ALL SELECT 'artifacts', count(*), max(created_at) FROM artifacts;
-- ② o silêncio é deliberado?      ③ o filtro do console casa?
SELECT name, agent_role, is_active, desligado_em FROM agents ORDER BY agent_role;
SELECT source, count(*) FROM broker_insights GROUP BY 1;
-- ④ o eixo do trabalho
SELECT workflow_key, count(*), count(*) FILTER (WHERE status='failed'),
       round(avg(extract(epoch from finished_at-started_at))::numeric,1) dur_s,
       round(avg(extract(epoch from started_at-created_at))::numeric,1) fila_s
  FROM work_runs WHERE created_at > now()-interval '30 days' GROUP BY 1 ORDER BY 2 DESC;
```
```bash
# ⑤ a lista dupla ainda diverge?   ⑥ os três pulsos mortos e os oito cruzados ainda estão lá?
grep -c '^    ("' backend/app/core/heartbeat.py                       # espere 14
grep -rn "cutover_ligado" backend/app/services/*.py | grep -v "def "  # espere 3 arquivos
grep -rn "await beat(\|await _beat(" backend/app --include=*.py | wc -l   # espere 27
```

**Gate do BLOCO 0:** ① as três causas (§1.4, §1.5, §1.6) continuam no código com o
`arquivo:linha` desta SPEC — se alguma já foi consertada, o item correspondente SAI e o
relatório diz · ② `AGENT_TASKS` tem 14 entradas; se tiver outro número, a tabela do BLOCO A
é REFEITA por medição · ③ o número de `workflow_key` em 7 dias é o que o BLOCO C tem de cobrir.

---

# BLOCO A · 🔴 Cada trabalhador declara o que PRODUZ, num lugar só

## O conserto

`AGENT_TASKS` (`backend/app/core/heartbeat.py`) deixa de ser lista de tuplas e passa a ser
o **registro único** dos trabalhadores digitais. Cada entrada ganha:

```
id · nome · descricao
grupo               observa | atende_agora | mantem_rota | aprende_avisa          (BLOCO D)
cor                 🔴 sai do frontend e vem para cá                               (mata a §1.6)
eixo                {"workflow_keys": [...]}  ou  {"redis": true}  — de onde vem o PULSO e o TRABALHO
fonte_de_producao   (tabela, coluna_de_tempo, filtro SQL opcional)  ou  None EXPLÍCITO
cadencia_esperada_s de quanto em quanto tempo ele DEVIA produzir; None se não se sabe
```

🔴 **E o registro cresce:** todo `workflow_key` visto em `work_runs` nos últimos 7 dias
que não tenha trabalhador entra — ou entra na lista `SEM_CARD_POR_DECISAO` com o motivo
escrito. 📊 Hoje faltam **cinco**: `detect_signals`, `measure_outcomes`, `daily_briefing`,
`weekly_executive_briefing`, `cluster_demand`. O executor cria os cards (💭 nomes de
produto: *Detector de sinais*, *Medidor de resultados*, *Briefing* — os dois briefings num
card, *Agrupador de demanda*) e liga `garimpo` a `intelligence.garimpo` e `auditor` a
`intelligence.investigate_quality`.

📊 **As fontes que a conversão mediu — o executor CONFERE, não copia:**

| id | fonte_de_producao | 📊 último em 03/09 | cadência 💭 |
|---|---|---|---|
| `observador` | `observed_events.created_at` | 26/08 13:52 | diária |
| `tecelao` · `cartografo` | `ura_maps.created_at` | 26/08 14:07 | semanal |
| `sentinela_rotas` | `route_drift.created_at` | 26/08 14:07 | diária |
| `espelho_atendimento` | `attendance_transcripts.created_at` | **03/09 01:39** | horária, quando há atendimento |
| `followup` | `platform_sends.created_at` | 19/08 19:41 | diária, quando há caso aberto |
| `garimpo` | `greatest` de `intelligence_signals` (`source_type='garimpo'`, `last_seen_at`) e `broker_insights` (`source LIKE 'garimpo%'`) | 26/08 00:05 | diária |
| `detector` (novo) | `intelligence_signals` · `source_type='detector'` · `greatest(last_seen_at, created_at)` | 02/09 04:04 | horária |
| `auditor` | `conversation_scorecards.created_at` | **03/09 00:04** | diária |
| `alfaiate` | `playbook_overlays.created_at` | ⛔ 0 linhas, nunca | — |
| `sugestoes` | `broker_insights` · `source='sugestoes_ia'` | ⛔ 0 de 270 | — |
| `briefing`, `medidor`, `agrupador` (novos) | `work_runs` do próprio `workflow_key`, `status='completed'` **e** `artifacts.work_run_id` quando houver | 03/09 | diária / horária / diária |
| `espelho` · `vigia_sentinela` · `cerebro` · `conselho` | 🔎 o executor mede e declara; se não achar tabela → `None` | — | — |

🔴 **Por que o `garimpo` usa `greatest()` das duas colunas e das duas tabelas:** o fluxo
canônico grava `intelligence_signals` e projeta em `broker_insights` (`garimpo_v3.py:106-108`,
`_projetar_legado :164`), a projeção é condicional ao dedupe, e no acerto de dedupe
`signal_service.py:144-167` move `last_seen_at`, não `created_at`. Um garimpo que só
reconfirma sinais não move `created_at` — e o card congelaria num agente saudável.

🔴 **A regra que fecha a porta:** agente sem `fonte_de_producao` mostra ⚫ NÃO MEDIDO.
**Nunca** 🟢. É a §7 do protocolo aplicada à própria Central, e o `no_policy` do Dagster.

⛔ **Não é uma tabela nova.** `max(coluna)` da tabela que o agente já escreve **é** o
histórico. Uma tabela `agent_health` seria um segundo lugar para a verdade.

## O gate
```
① as 14 + as novas entradas têm grupo, cor, eixo, fonte (ou None explícito) e cadência (ou None) — nenhum implícito
② 🔴 TODO workflow_key visto em work_runs nos últimos 7 dias tem trabalhador OU está em SEM_CARD_POR_DECISAO com motivo.
   Lista vazia com workflow_key sem card REPROVA. 📊 Hoje reprovariam 5
③ 🔴 o frontend NÃO tem lista de agente: nem cor, nem nome, nem grupo (`grep` no diretório da página → 0)
④ toda fonte_de_producao aponta para tabela e coluna que EXISTEM (o teste consulta information_schema)
```
**Mutação:** apague a `fonte_de_producao` de um agente → ① fica vermelho e o card dele vira
⚫. Acrescente um `workflow_key` inventado à lista de 7 dias (fixture) → ② fica vermelho.

---

# BLOCO B · 🔴 Cinco estados, e o verde é o mais difícil de conseguir

```
🟢 SAUDÁVEL            pulsou  E  produziu dentro de k × cadência DELE          (k = 2, calibrável por agente)
🟡 PULSA SEM PRODUZIR   o laço roda (pulso ou run completed recente) e a produção passou do limiar  ← o Garimpo hoje
⚪ DESLIGADO            agents.is_active = false em TODAS as corretoras, e diz desde quando (ou "sem registro")
🔴 PARADO               devia pulsar na cadência dele e não pulsa — inclui chave de heartbeat EXPIRADA
⚫ NÃO MEDIDO           sem fonte declarada, ou sem correspondência entre AGENT_TASKS e agents
```

🔴 **O pulso tem duas origens, e a do motor vale mais:** para trabalhador com `eixo.workflow_keys`,
o *last_run* é `max(work_runs.finished_at) WHERE status='completed'`, e falha é
`status='failed'`. O Redis fica para os 10 que só vivem lá. **Nunca os dois competem:** o
eixo declara qual.

🔴 **DESLIGADO sai de um fato do banco.** 📊 `agents`: 4 `attendance` false, 3 `core` true,
1 `core` false; `desligado_em` NULL em 8 de 8. Sem data → *"sem registro"*, nunca uma data
inferida. `is_active` é por corretora e o card é de plataforma → regra `all()`. Não existe
chave entre os 8 `agents.slug` e os ids de `AGENT_TASKS`: agente sem correspondência mostra
⚫, nunca ⚪. **A dúvida paga do lado de quem alerta** (referência ⑤).

⚠️ **D3 (`attendance_capture.py:378`, `_beat(0)`) NÃO é removido.** Com a regra nova ele é
honesto: pulsou e não produziu → 🟡.

## O gate
```
① o Garimpo de hoje (run completed há 1 MINUTO, produção de 26/08) → 🟡, NUNCA 🟢
   🔴 o teste força last_run = agora: é a janela exata em que o código de hoje pinta 🟢
② agente is_active=false em TODAS as corretoras → ⚪ com "sem registro"; uma corretora ligada → NÃO é ⚪
③ agente sem fonte → ⚫
④ 🔴 chave de heartbeat expirada (morte de 30 dias) → 🔴 PARADO. O _TTL de 7 dias não transforma morte antiga em ⚪
⑤ agente que roda 1×/dia (auditor) com produção de 20h atrás → 🟢, não 🔴: o limiar é DELE
⑥ 🔴 LINHA DE CONTROLE: pulsou E produziu na cadência → 🟢. Sem ela, um guarda que pinta tudo de amarelo passaria em ①–⑤
```
**Mutações (duas):** force `last_run = agora` com produção parada → ① tem de dar 🟡; force a
chave a expirar → ④ tem de dar 🔴. Se der ⚪, o D4 da v1 continua vivo com teste verde.

---

# BLOCO C · A rota lê o TRABALHO — execuções, falhas, entregas, travamentos, aprovações

## O conserto

`GET /api/admin/spec034/agents-status` (mesmo caminho, `require_master_admin`) passa a
devolver o **contrato da §5**, calculado no backend com **cache de 60s em Redis** (📊 a
tela recarrega a cada 20s; 20 consultas × 3/min contra produção seria autogol). O leitor
mora num módulo novo ao lado do heartbeat (💭 `backend/app/core/central_de_agentes.py`),
e **não** cria tabela.

Para cada trabalhador com `eixo.workflow_keys`, a partir de `work_runs` e das tabelas
ligadas por `work_run_id` (📊 índices existem nas três):

```
execucoes_24h · execucoes_7d · falhas_7d              work_runs por workflow_key e status
duracao_media_s · fila_media_s                        finished_at-started_at · started_at-created_at
artifacts_7d                                          artifacts.work_run_id → work_runs.workflow_key
aprovacoes_pendentes                                  approval_requests.status='pending' → work_run_id
travados                                              work_runs.unblock_state='travado'
custo_brl_30d                                         sum(cost_actual_brl)  — 📊 hoje 0,00 em todos, e o card DIZ "0,00 (não instrumentado)"
```
Para os 10 que vivem só no Redis: `trabalho = null` e a tela escreve *"sem eixo de
trabalho"* — nunca zeros que pareçam medição.

🔴 **Nada de conteúdo atravessa** (referência ⑦): a rota devolve contagens, estados, ids,
timestamps. O guarda do BLOCO F confere.

🔴 **O filtro do console `/admin/insights`** (`admin_spec034.py:90` `"garimpo"` e `:99`
`"sugestoes_ia"`; 📊 o banco só tem `garimpo_v3`) sai do código e lê a mesma
`fonte_de_producao` do BLOCO A. Não é trocar a string: é matar a classe.

## O gate
```
① a rota devolve o contrato da §5 em UMA chamada, com `gerado_em` e `cache_s`
② para intelligence.detect_signals: execucoes_7d > 0 e falhas_7d = 0 (📊 hoje 504 e 0) — o motor invisível aparece
③ 🔴 LINHA DE CONTROLE: banco sem run de um workflow_key → execucoes = 0 SEM erro, e o card diz 0
④ o ranking de /admin/insights devolve > 0 com 270 linhas no banco; com banco vazio devolve 0 sem erro
⑤ 🔴 DOIS TENANTS: nenhuma rota de corretora serve agents-status nem o agregado. require_master_admin provado no teste, não presumido
⑥ nenhum campo do JSON contém texto de conversa: o teste lista as chaves e reprova qualquer uma fora do contrato
⑦ next start + 1 requisição autenticada a /api/admin/spec034/agents-status responde 200 (CLAUDE.md §9.1)
```
**Mutação:** troque uma `fonte_de_producao` por `tabela_que_nao_existe` → gate ④ do BLOCO A
e este ③ ficam vermelhos. Restaure por cópia.

---

# BLOCO D · Os quatro grupos numa tela — a queixa do Founder, respondida

```
👁️ OBSERVA E REGISTRA      o que aconteceu ficou gravado          observador · tecelao · espelho · espelho_atendimento · cartografo
🚑 ATENDE AGORA            alguém está esperando neste minuto      vigia_sentinela · cerebro · followup     🔴 o único grupo que alcança o segurado
🧭 MANTÉM A ROTA CERTA     a seguradora mudou e nós acompanhamos   sentinela_rotas · alfaiate
🎓 APRENDE E AVISA         ontem virou conserto e recomendação     garimpo · detector · auditor · sugestoes · conselho · briefing · medidor · agrupador
```

Cada grupo abre com **uma linha de resumo** que o Founder lê em três segundos: `3 de 4
saudáveis · 1 pulsa sem produzir` · `4 desligados · sem registro de quando`. Cada card
mostra o estado, o motivo em uma frase, e um painel dobrável **TRABALHO** com os números
do BLOCO C, ou *"sem eixo de trabalho"*. O bloco MEMÓRIA existente permanece.

⚠️ **Uma tela, não quatro páginas.** 📊 `lib/navigation.ts:MENU_NAO_CRESCE = 5`, guardado
por `backend/tests/test_menu_nao_cresce.py`. Quatro páginas para ~20 cards adiciona
navegação para consertar navegação. 🧑 **F-088-01:** se agrupado ainda parecer confuso, a
próxima peça é uma página por grupo, e aí o menu muda por escrito. Não bloqueia.

**Referência de forma:** `docs/canon/DS-001-design-brief.md` §5; telas admin vizinhas
`app/admin/trabalhos/page.tsx`, `app/admin/aprovacoes/page.tsx`. A página continua
`'use client'` e sem componente compartilhado novo, a menos que o builder encontre um
card reutilizável já existente.

## O gate
```
① todos os trabalhadores aparecem, em 4 grupos, e o grupo vem do JSON (BLOCO A) — o frontend não sabe nomes
② 🔴 um trabalhador NOVO no JSON aparece sem mudar o frontend (teste de render com fixture de 21 agentes)
③ cada grupo tem a linha de resumo e o número dela bate com os cards
④ o card mostra o motivo do estado e, quando há eixo, o painel TRABALHO com os 8 números; sem eixo, "sem eixo de trabalho"
⑤ test_menu_nao_cresce.py continua verde
⑥ npm run test:rotas-montam verde (mexeu em app/)
```
**Mutação:** fixture com um agente sem `grupo` → o render mostra o grupo `SEM GRUPO` em
vermelho e o teste ② reprova. Se ficar verde, a SPEC reconstruiu a §1.6.

---

# BLOCO E · Os pulsos: três mortos e oito cruzados

```
E1  os 3 pulsos atrás de cutover_ligado()  (§1.4)
    🔴 garimpo e auditor: o pulso passa a vir do EIXO (work_runs do workflow_key) — o beat() morto
       é REMOVIDO, não consertado no lugar. Para sugestoes, que não tem workflow nem outro pulso:
       o beat() sai do ramo morto e vai para o fluxo que roda de fato — ou o executor prova que
       nada roda e o card fica ⚫ com motivo "sem fluxo ativo desde o cutover"
E2  os 8 pulsos cruzados (§1.5): cada agente dá o próprio pulso, ou não dá nenhum.
    As três do alfaiate vão para playbook_tailor.py, a casa dele (📊 0 beat hoje)
E3  🔴 nenhum beat() dentro de finally: — em NENHUM dos 18 arquivos. Caminho de exceção não pinta card
```
## O gate
```
① grep -rn "cutover_ligado" nos 3 arquivos: nenhum beat() depois de um return dele
② 🔴 nenhum beat("x") fora do módulo do x — teste que mapeia call site → agente e reprova cruzamento (📊 8 hoje)
③ nenhum beat( dentro de finally: (📊 1 hoje)
④ 🔴 LINHA DE CONTROLE: o pulso legítimo de dispatch_watchdog.py:622 continua e o card do vigia_sentinela pulsa no teste
```
**Mutação:** reintroduza um `await beat("alfaiate")` em `conversation_auditor.py` → ② vermelho.

---

# BLOCO F · O guarda — no formato do `test_o_protocolo_tem_policia.py`

Um arquivo `backend/tests/test_a_central_diz_a_verdade.py`, com blocos e linha de controle,
cobrindo os gates ②③④ do A, ①–⑥ do B, ③④⑥ do C, ②③ do E. Roda sem banco onde puder
(fixtures) e com banco onde a SPEC exige (`information_schema`, dois tenants).

**Mutações obrigatórias do guarda, e são três:** apague uma `fonte_de_producao` → vermelho ·
troque o limiar único de volta para 900s global → o gate ⑤ do B fica vermelho · force a
chave expirada a virar ⚪ → o gate ④ do B fica vermelho. Restaurar por cópia.

---

## 4. O CONTRATO DA ROTA — congelado para os builders trabalharem em paralelo

```json
{
  "gerado_em": "2026-09-03T02:10:00Z", "cache_s": 60,
  "grupos": [
    {"id": "aprende_avisa", "titulo": "APRENDE E AVISA", "proposito": "ontem virou conserto e recomendação",
     "resumo": "3 de 8 saudáveis · 1 pulsa sem produzir · 2 não medidos",
     "agentes": [
       {"id": "garimpo", "nome": "Garimpo", "descricao": "...", "cor": "#...", "grupo": "aprende_avisa",
        "estado": "PULSA_SEM_PRODUZIR",
        "motivo": "21 execuções completas em 7 dias; última produção em 26/08 (8 dias); cadência esperada 1 dia",
        "pulso": {"ultimo": "2026-09-03T00:01:03Z", "origem": "work_runs"},
        "producao": {"ultimo": "2026-08-26T00:05:34Z", "fonte": "broker_insights.created_at ∪ intelligence_signals.last_seen_at",
                     "cadencia_esperada_s": 86400, "limiar_s": 172800},
        "desligado": {"todas_desligadas": false, "desde": null},
        "trabalho": {"eixo": ["intelligence.garimpo"], "execucoes_24h": 3, "execucoes_7d": 21, "falhas_7d": 0,
                     "duracao_media_s": 9.9, "fila_media_s": 35.7, "artifacts_7d": 0,
                     "aprovacoes_pendentes": 0, "travados": 0, "custo_brl_30d": 0.0, "custo_instrumentado": false},
        "acoes_hoje": 0}
     ]}
  ],
  "sem_card_por_decisao": [{"workflow_key": "bridge.routine.execute", "motivo": "ponte de rotina, contada no auxiliar"}]
}
```
`estado` ∈ `SAUDAVEL | PULSA_SEM_PRODUZIR | DESLIGADO | PARADO | NAO_MEDIDO`.
`trabalho` é `null` quando o eixo é só Redis. Nenhuma chave fora desta lista.

---

## 5. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

📊 A proposta tem 3.718 linhas; o research-pack, 1.180 e 13 referências. O que entra é a
saúde e a visão por trabalhador. O runtime de delegação fica para a **SPEC-088-B**, e o
gatilho é medido:

| peça da proposta | 📊 medido em 03/09 | volta quando |
|---|---|---|
| contratos de delegação, DelegationEnvelope, ResultEnvelope | `agent_delegations` = **0 linhas** | existir a primeira delegação real |
| Admission Gate, Parallel Group, Lead/Orchestrator, depth, fanout | 8 agentes = 2 por corretora | houver 3+ agentes disputando o mesmo pedido |
| Agent Role Spec e releases | o Skill Registry (20 skills) já versiona procedimento | um papel precisar de versão própria |
| juízes e AAA profile dentro do produto | o painel é do PROTOCOLO | ⛔ v11 §5.1: juiz julga código, não documento |
| peer teams, mailbox, task DAG | pack §56: NÃO na V1 | eval provar ganho |
| custo por trabalhador via `usage_events` | 400 eventos, **0** com `work_run_id`; `cost_actual_brl` = 0 em 3.494 runs | 🔴 **P-088-CUSTO**: o callback passa `work_run_id` e o worker grava `cost_actual_brl`. Bloco de ~1–2h, fora desta SPEC porque exige decidir onde vive o contexto de run no chat |
| Quality Health / eval de saída | `conversation_scorecards` já dá nota | 088-B |

Nada foi julgado ruim. Foi julgado cedo, e cada linha tem gatilho.

---

## 6. ⛔ POR QUE ZERO MIGRATION — decisão, não esquecimento

A produção sai de `max(coluna)` das tabelas que os agentes já escrevem; o trabalho sai de
`work_runs` e das três tabelas já indexadas por `work_run_id`; o estado é calculado na
leitura com cache de 60s. REVERSIBILIDADE 0: desfeito o commit, as chaves do Redis
expiram e não sobra estrutura. Uma tabela `agent_health` teria posto a SPEC em CRÍTICO e
criado um segundo lugar para a verdade.

---

## 7. O que fica pendente

```
P-088-01  knowledge_cards parado desde 16/08 — 📊 18 dias, 18.715 linhas. Esta SPEC faz o silêncio APARECER; não religa o destilador.
P-088-02  playbook_overlays = 0 desde sempre. Depois desta SPEC o Alfaiate fica 🔴/⚫ o tempo todo — é a informação certa.
P-088-03  platform_sends = 5, última 19/08. Se é a fonte do Follow-up, ele está mudo há 15 dias. Confirmar a fonte (BLOCO A).
P-088-04  P-70 continua: o Follow-up pergunta ao segurado e ninguém lê a resposta.
P-088-05  O 6º pilar Memórias é exceção temporária de 18/08 (lib/navigation.ts). 🧑 do Founder.
P-088-06  📊 122 de 175 tabelas com RLS e zero policies (P-090-01). Não é desta SPEC; ela não cria tabela.
P-088-CUSTO  📊 usage_events 30d: 400 linhas, 0 com work_run_id; correlation_id não casa (0 de 394);
          work_runs.cost_actual_brl = 0 em 100%. Custo por trabalhador não existe hoje. Conserto: cost_callback.py:252-274
          passa work_run_id/work_step_id do contexto de run; o worker grava cost_actual_brl. ~1–2h, próxima leva.
P-088-ARTIFACTS  📊 33 de 118 artifacts (30d) sem work_run_id — 6 chamadores de ArtifactService não passam o id
          (relatorios_comerciais.py:178, report_tool.py:263, billing_collection.py:1439, research/adapters.py:348,
          research/radar.py:389, api/artifacts.py:64,70). Entregas órfãs não aparecem no card. ~1h.
P-088-AUX  auxiliary_events: escritor em factory.py:460-471, ZERO chamadores (P-18 confirmada). Os auxiliares
          instalados (9) não têm eixo de trabalho até WORK_RUNS_ROUTINE_BRIDGE ligar (📊 7 runs históricos).
```

## 8. 🧑 A CAIXA DO FOUNDER

```
F-088-01  Uma tela com 4 grupos, não 4 páginas. Se ainda parecer confuso, a próxima peça é uma página por grupo
          e o menu muda por escrito. Não bloqueia.
F-088-02  A SPEC-088-B (runtime de delegação: admission gate, envelopes, grupos paralelos) fica adiada com gatilho
          medido: agent_delegations = 0. Quando houver o primeiro caso real de 3+ agentes no mesmo pedido, ela volta.
F-088-03  Custo por trabalhador é pendência (P-088-CUSTO), não bloco: exige decidir onde vive o contexto de run
          no chat. A tela dirá "0,00 (não instrumentado)" em vez de fingir zero.
```

## 9. A ordem de execução

```
BLOCO 0  →  {A+B+C}  ‖  {D contra o contrato da §4}  ‖  {E}  →  F (gates)  →  verificador  →  painel de 3 lentes  →  conserto  →  juiz de confirmação
```
🔴 A e B e C são de UM builder (mesmo módulo, mesma interface). D e E correm em paralelo
porque o contrato está congelado e os arquivos são disjuntos. A integração é serial e a
suíte inteira roda no fim de cada bloco integrado e no fim.

💭 **5–8h.** O BLOCO A+B+C domina: declarar e conferir ~20 fontes e eixos, quatro delas por
medição do executor.
