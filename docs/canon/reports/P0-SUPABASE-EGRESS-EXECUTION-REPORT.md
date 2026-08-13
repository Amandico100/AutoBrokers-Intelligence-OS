---
> **Status:** relatório de execução — P0 de infraestrutura
> **Data:** 13/08/2026 · **Branch:** `fix/p0-espelho-egress` → `main`
> **Commit inicial:** `adf64d4` · **Commit final:** `05fb3ae`
> **Change Addenda:** CA-034 (BLOCKER, executada) · CA-035 · CA-036
---

# P0 — Supabase Egress: o recovery do Espelho virou um leitor do próprio histórico

## 1. O que aconteceu

**FATO.** A organização Supabase foi restringida por Fair Use no ciclo
05/08 → 05/09/2026: cota Free de 5 GB, **6,98 GB consumidos**, overage de
1,98 GB. Produção passou a responder **HTTP 402** em PostgREST, Storage e Auth.
O portal-worker parou de enxergar `portal_jobs`, e a conclusão da MAPFRE ficou
bloqueada por consequência.

**FATO.** A causa dominante é `sincronizar_chats()` +
`espelhar_no_chat()`. O job de recuperação relia a janela de 7 dias de
`attendance_transcripts` a cada ciclo e, para **cada linha**, carregava as 40
últimas mensagens da conversa para deduplicar.

---

## 2. A evidência

📊 Medido em 13/08/2026 pela **Management API do Supabase** — que continua
respondendo apesar do 402 em PostgREST.

### 2.1 O contador do Postgres

| Consulta (PostgREST) | calls | linhas/call | bytes/linha | atribuído |
|---|---:|---:|---:|---:|
| `messages(id, content, created_at, payload) LIMIT 40` | **771.313** | 33 | 290 | **~7.040 MB** |
| `users_v2(id, first_name, last_name)` | 776.542 | 1 | ~95 | ~70 MB |
| `conversations(id, status)` | 776.338 | 1 | ~60 | ~44 MB |
| `work_queue_outbox(*)` — resposta vazia | 712.971 | 0 | ~40 | ~27 MB |

As três primeiras são **exatamente** as três consultas de `espelhar_no_chat`,
em contagens quase idênticas — assinatura 1:1:1. Nenhuma outra consulta do
repositório usa aquele conjunto de colunas (conferido por `grep` em todos os
leitores de `messages`).

### 2.2 A atribuição temporal

A coluna `payload` **só existe desde 06/08** (migration `20260806_01`), logo os
771.313 calls são **todos** posteriores ao Espelho. Primeira mensagem espelhada:
**06/08 23:25:39 UTC**. O salto do gráfico de Egress é **07/08**.

### 2.3 O contador do próprio produto — instrumento independente

📊 Lido em `/health` às 19:25 UTC de 13/08, do Redis:

```
ja_estava:      746.484
mensagem_nova:    5.718
conversa_nova:      101
```

**746.484 "já estava" para 5.819 escritas úteis.** Dois instrumentos
independentes — `pg_stat_statements` e o contador Redis do produto — chegam ao
mesmo número. Essa é a confirmação mais forte do relatório.

### 2.4 O número que resume

> **136 leituras de `messages` para cada mensagem escrita.**
> 99,3% do trabalho foi descobrir que a mensagem já estava lá.

### 2.5 Hipóteses REFUTADAS por medição

| Hipótese | Medição | Veredito |
|---|---|---|
| Realtime | zero tabelas em `supabase_realtime` | **refutada** |
| Storage / mídia | 94 objetos, 11 MB | **refutada** |
| Banco cheio | 241 MB | **refutada** |
| RAG / Qdrant | serviço separado, não gera Egress Supabase | **refutada** |
| Polling do outbox | 712.971 calls, ~27 MB = **0,4%** | não é a causa (é P1) |

### 2.6 O achado que refutou a correção óbvia

**FATO.** 776.542 calls ÷ 6,77 dias ÷ 4.008 linhas por ciclo = **~28,6
ciclos/dia** — um ciclo a cada ~50 min, não a cada 10. Com `max_instances=1`, o
agendador **já descartava 4 de cada 5 disparos**. O laço rodava saturado.

**Consequência:** aumentar `ESPELHO_SYNC_INTERVAL_MINUTES` de 10 para 30 **não
reduziria o Egress em nada**. Seria uma correção que parece funcionar, não mede,
e devolve o problema. Só reduzir o *trabalho por ciclo* resolve.

---

## 3. O que foi feito

### Alavanca A — `51b5c0f`

A leitura de 40 mensagens servia **duas** perguntas e pagava o preço da mais
cara para responder a mais barata.

| Pergunta | Antes | Depois |
|---|---|---|
| já está no chat? | 40 linhas (~9,5 kB), sempre | `INSERT`; o índice único responde `23505` |
| é eco do dashboard? | mesma leitura | só se `out` + texto + < 300 s → ~0–3 linhas |

O índice `messages_espelho_sem_duplicata_uidx` **já era** a garantia definitiva —
o próprio código chamava o Python de "atalho". O atalho custava mais que o
caminho.

**Portão a 300 s, regra de negócio a 120 s.** `quando_iso` vem do relógio do
WhatsApp; um desvio de dois minutos fecharia a porta na cara de um eco legítimo.

### Alavanca B — `d9d17bb`

Marca d'água durável por corretora, no **relógio de ingestão**.

🔴 **O cursor é `created_at`, nunca `wa_timestamp`.** 📊 Medido:

| `source` | linhas | atraso médio | atraso máx | **> 15 min** |
|---|---:|---:|---:|---:|
| `history_sync` | 99.951 | 3.981 h | 16.293 h | **99.845 (99,89%)** |
| `live` | 5.324 | 0,0 h | 0,1 h | 0 |

Mensagem **enviada** em setembro/2024 foi **inserida** em agosto/2026 — 679 dias
depois. Um cursor por `wa_timestamp` não veria 99,89% dessas linhas. Elas
ficariam intactas no acervo e **nunca** apareceriam no chat. (`wa_timestamp`
também é NULLABLE — cursor sobre coluna que aceita NULL está quebrado por
construção.)

As outras quatro garantias:

- **Partida a frio.** Sem cursor = nasce em `now()`, **não varre**. O acervo tem
  105.275 linhas; uma varredura automática seria 26× o ciclo que causou o
  incidente, no minuto seguinte ao Upgrade.
- **Atraso de segurança de 5 min.** `now()` no Postgres é o início da transação,
  não o commit. A ponte ao vivo não é afetada.
- **O cursor não avança sobre erro.** Só ultrapassa
  `DESFECHOS_DETERMINISTICOS`.
- **Uma regra só de elegibilidade.** O backfill **não** chamava `deve_espelhar`:
  ao vivo valia 30 dias, pelo acervo valia 7. Duas regras para a mesma pergunta,
  escolhidas pelo caminho que a mensagem tomou.

### Migration `20260813_01` — expand-only, APLICADA e VERIFICADA

```
VERIFY (13/08 18:4x UTC)
  tabela espelho_sync_cursor .......... existe
  ix_attendance_transcripts_cursor .... existe
  RLS fail-closed ..................... true
  cursores semeados ................... 3 (todos no presente, 0 no passado)
  attendance_transcripts .............. 105.275  INTACTA
  messages ............................   6.447  INTACTA
  conversations .......................     223  INTACTA

EXPLAIN ANALYZE com company_id literal (como a aplicação envia):
  Index Scan using ix_attendance_transcripts_cursor
  Index Cond: company_id AND created_at >= ... AND created_at < ...
  Buffers: shared read=3 · Execution Time: 5.721 ms · SEM nó de ordenação
```

---

## 4. Testes — com saída real

```
tests/test_o_espelho_vira_conversa.py ........... TUDO VERDE
tests/test_quem_fala_primeiro_cala_o_outro.py ... TUDO VERDE
tests/broker_outcome_regression_pack.py ......... passaram=47  falhas=1  total=48
```

A falha é **SEC-05**, **pré-existente e alheia** a este P0: o caso procura a tela
de conversas em dois caminhos e a tela mudou de casa (SPEC-043/064). Prova de
que não foi causada aqui: os três commits tocam **zero** arquivos em `app/`
(`git diff --stat origin/main..HEAD -- app/` = vazio). Sem exposição real —
a tela verdadeira não usa `supabase.storage` nem `createClient`. Registrado em
**P-124**.

### 4.1 O teste que mede o ganho

```
[9] Um ciclo sem novidade não relê o chat inteiro
  OK  a primeira passada grava as 50 mensagens
  OK  a segunda passada não escreve nada
  OK  🔴 e não lê `messages` NENHUMA vez  (0 leituras — o desenho antigo fazia 50)
  OK  CONTROLE — o acervo ainda é lido (1 página)
  OK  CONTROLE — nem a PRIMEIRA passada lê `messages`

[9b] CONTROLE — a leitura de eco acontece quando pode haver eco
  OK  mensagem de saída recente: o eco É consultado  (1 leitura)
  OK  CONTROLE — mensagem de saída ANTIGA não consulta o eco
  OK  CONTROLE — mensagem do CLIENTE não consulta o eco
```

O par `[9]`/`[9b]` importa: sozinho, `[9]` ficaria verde se alguém apagasse o
guarda de eco inteiro.

### 4.2 Mutações — prova de que cada guarda consegue reprovar

| Mutação | Resultado |
|---|---|
| portão do eco em 0 s | 2 controles **VERMELHOS** |
| checagem de eco removida | 2 controles **VERMELHOS** |
| índice único removido | 4 controles **VERMELHOS** |
| cursor volta a `wa_timestamp` | 2 controles **VERMELHOS** (a de 2024 não é **lida**) |
| sem cursor passa a varrer | 2 controles **VERMELHOS** |
| atraso de segurança a zero | 1 controle **VERMELHO** |
| cursor avança sobre erro | 4 controles **VERMELHOS** |

📊 A mutação do `wa_timestamp` reprovou primeiro por um controle **fraco** — a
linha de 2024 não aparecia no chat, mas por nunca ter sido lida. A asserção foi
reescrita para medir o que foi **LIDO**, não o que apareceu: "não apareceu" tem
duas explicações e só uma é aceitável.

### 4.3 Dublês fortalecidos (CLAUDE.md §9.3)

- `test_quem_fala_primeiro` não tinha `gte` e **ignorava `order`**. Era mais
  fraco que o banco real. Deu certo por acaso — ele falhou barulhento; um `gte`
  permissivo teria deixado três controles de eco **verdes** enquanto o guarda
  lia a conversa inteira em produção.
- O mesmo dublê passou a impor o índice único. Sem ele, a dedup — que agora
  depende **só** do banco — ficaria verde por permissão.

### 4.4 Guardas migrados, não mortos

Dois guardas afirmavam verdades que venceram:

1. `.gte("created_at", desde)` proibido no arquivo inteiro. `created_at` ganhou
   uso legítimo (eco e cursor). A regra que **não** venceu é mais estreita — a
   elegibilidade é julgada por `wa_timestamp` — e o guarda passou a olhar só a
   função que lê o acervo, com controle que prova que o recorte não veio vazio.
2. "a janela do sync é a mesma da lista". O sync não tem mais janela, tem cursor.
   A regra escondida ali estava sendo **violada sem ninguém ver**: a
   elegibilidade era diferente nos dois caminhos. Agora há guarda que lê os três.

---

## 5. Rollback

| | Como reverter | Migration | Perda de dados |
|---|---|---|---|
| **A** `51b5c0f` | `git revert` | nenhuma | **nenhuma** |
| **B** `d9d17bb` | `ESPELHO_SYNC_ENABLED` fora, ou `git revert` | expand-only | **nenhuma** |

No rollback operacional, **não derrubar** `espelho_sync_cursor`: basta reverter
o código e a tabela fica inerte. `attendance_transcripts` (105.275 linhas)
permanece intacta e permite reconstruir o Espelho inteiro.

---

## 6. Multi-tenant

Cursor **por `company_id`** (chave primária — impossível uma corretora ter dois
cursores em desacordo). Leitura filtrada por `company_id`. RLS fail-closed na
tabela nova. Teste com dois tenants: *"CONTROLE — nada da Amandus apareceu na
AutoFleet"* — verde.

---

## 7. Nenhum motor paralelo foi criado

Nada de runtime, RAG, memória, publisher, scheduler, executor, registry, fila,
Control Plane ou Ledger novo. O sync continua no `buffer_processor` que já
existe. O backfill dirigido usa o endpoint que já existe. A dedup usa o índice
que já existe.

**Não tocado:** Qdrant · RAG · `knowledge_cards` · Memory Fabric ·
`user_memories` · `session_summaries` · corpus normativo · DocumentService ·
IngestionService · MinIO · mídia · `integrations` · outbox · Work Runs ·
MAPFRE · Zurich · D11 · `attendance_transcripts` (dados).

---

## 8. Riscos remanescentes

| Risco | Mitigação |
|---|---|
| Eco aparecer duas vezes | portão a 300 s (2,5× a regra); 2 mutações provam o guarda |
| Recovery pular mensagem | cursor de ingestão + atraso 5 min + não avança sobre erro; 3 mutações |
| Duplicata no chat | garantia é o índice único do Postgres, sem janela |
| Cursor não ligado por esquecimento | **P-122** |
| Janela da pane não recuperada | **P-123** |
| Gate vermelho crônico por SEC-05 | **P-124** |

---

## 9. Estado do serviço no fim desta sessão

📊 13/08 19:25 UTC, `/health` da API:

```
HTTP 503 · Server: uvicorn        ← a API RESPONDE; o 503 é o veredito dela
status: unhealthy                    sobre a dependência, não queda de processo
database_sync: disconnected  →  "exceed_egress_quota ... must upgrade their plan"
redis: conectado · qdrant: conectado · storage: conectado
GET / → 200 · WEB → 200
PostgREST direto → 402
```

O 402 persiste — como esperado. É o Founder quem o remove.
