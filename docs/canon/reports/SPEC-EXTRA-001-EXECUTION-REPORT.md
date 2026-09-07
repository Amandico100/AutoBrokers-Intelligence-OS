# Relatório de execução — SPEC-EXTRA-001: A operação dos pilotos

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2)

```
OUTCOME ..............  a corretora escolhe ENCAMINHAR PARA A EQUIPE (atendente recebe nota interna + texto limpo + PDF) ou ENVIAR AO CLIENTE
                        (segurado recebe texto limpo + PDF pelo WhatsApp já pareado); cada parcela é cobrada UMA vez, com reserva antes do
                        efeito e estado por componente; a resposta do cliente chega ao atendimento com o caso certo e fica registrada mesmo
                        com o agente desligado; toda falha vira pendência visível; observador, QR, sessões e o modo teste de 17/08 não mudam
RISCO ................  8 = ALCANCE 3 + REVERSIBILIDADE 3 + FREQUÊNCIA 2
SUPERFÍCIE ...........  3 (📊 5 arquivos-hub: billing_collection 1.799 · platform_outbound 1.209 · webhook 1.997 · PainelDeRotinas 1.057 · rotinas/route.ts)
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" + migration de estrutura em billing_sent_log → CRÍTICO
NÍVEL ................  CRÍTICO · opção B (desenhista · 2 lentes + red team · juiz fresco)
UNIDADES .............  U0 medir · U1 motor+porta+migration · U2 respostas/convivência · U3 tela e rotas Next · U4 guardas · U5 canário · U6 docs/dossiê
COESÃO ...............  U1 = billing_collection + platform_outbound + migration (a porta) · U2 = billing_replies + webhook · U3 = Next (PainelDeRotinas hub)
PARALELISMO REAL .....  U1 ∥ U3 em arquivos disjuntos · U2 depois de U1 · integração serial
TIME .................  investigador+pesquisador (orquestrador) · aquecimento Opus · desenhista Opus · builders Opus (3) · verificador Sonnet ·
                        lentes verdade+regressão e produto+DADO · red team · juiz fresco
REFERÊNCIA ...........  interna: CLAUDE.md §7 · test_a_cobranca_esta_como_estava.py (34/34) · test_spec078_bloco_a_seguranca.py (39/39) ·
                        send_to_client_guarded · canario_098.py · externa: SPEC §7 (Postgres constraints · AWS outbox · Stripe webhooks · WhatsApp policy)
GATES ................  gate zero VERMELHO (📊 32 em 50d2b4e) · G00–G28b (SPEC §8) · mutações M1–M22 por nome (📊 22/22 vermelhas) · canário Q1–Q6 (pendente do Implantar) · suíte inteira ×2 · push
O ELO ................  "o cliente não recebe PORQUE a porta exige o agente ligado e escolhe integração sem para=auxiliar" — A medido (4/4 agentes
                        desligados), B medido (platform_outbound.py:948-990 · integration_service.py:274-298), B chega em A ✅ (o ramo live nunca
                        chama a porta; chamando, cairia em agente_desligado/sem_canal)
FAIXA DE RELÓGIO .....  declarada 8–13 h · real ≈ 14 h em 2 janelas (07/09 ≈ 00:30 → ≈ 08:30 limite de sessão com o juiz fresco no meio; retomada → ≈ 10:30) · continuou além da faixa
                        porque o painel achou 1 blocker de produto + 2 de procedimento e o juiz fresco 2 buracos de guarda — segurança e aceite não provado são MATERIAIS (§9.1)
ORÇAMENTO ............  ≤ 2,5 M · gasto 📊 ≈ 1,81 M contados (aquecimento 138k · desenhista 369k · U1 356k · U3 135k · U2 178k · verdade 155k · produto+DADO 172k ·
                        red team 210k · juiz fresco 97k) + 💭 ≈ 0,02 M do juiz morto pelo limite. Dentro do orçamento pela primeira vez numa CRÍTICO
```

### 🔴 As três perguntas que fecham o card
```
① o PAINEL rodou?           SIM — 3 lentes cegas de uma vez (verdade+regressão 87 · produto+DADO 88 · red team 86): 1 blocker de produto (B1, achado por DUAS lentes),
                            2 de procedimento do canário, 3 fraquezas de 2ª barreira, 20+ pendências — conserto único (95cd7dd · 5292fc9 · f11f543)
② a AUDITORIA / juiz fresco? SIM — §6.1, contexto novo, PASS COM PENDÊNCIAS 88: o conserto não criou defeito de produto; banco reconstruído por SELECT bate com o
                            contrato; 2 buracos de GUARDA (o chamador não coberto; a lista da equipe falhava aberta) + 2 pendências → fechados em 0be100a (G28b, M22)
③ pendências por VALOR MARGINAL: P-E001-ROUTINES-POR-INBOUND (cache), P-E001-RETORNO-IDEMPOTENTE-POR-CONTEUDO (message_id), P-E001-AGENT-ACTIVITIES-FORA-DA-FIXTURE,
                            P-E001-GET-INTEGRATION-SEM-TENANT, P-E001-LEDGER-SEM-VENCIMENTO-E-VALOR — nenhuma muda um byte do que chega hoje
```

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md`
**Branch:** `feat/spec-extra-001-operacao-pilotos`
**Worktree:** `AutoBrokers-FIX` (📊 preflight 07/09/2026: HEAD = origin/main = `34424fa`, 0 atrás, 0 à frente)
**Executor:** Fable 5.1 (orquestrador) · Opus 5 (aquecimento, desenhista, builders, lentes, red team, juiz) · Sonnet 5 (mecânico)
**Início:** 07/09/2026 · **Conclusão:** 07/09/2026
**Commit inicial:** `34424fa576f8fdb35f687e3a3af5c66a6e07f915`
**Commit final:** `0be100a` (código) · o commit do relatório/dossiê vem depois
**Estado final:** **CONCLUÍDA COM RESSALVAS** — implementada, gateada e na main; a prova VIVA (canário Q1–Q6 e o 23505 concorrente) depende do Implantar + 2 variáveis (caixa do Founder); aceite das pilotos não iniciado

---

## 0. Declaração de integridade
- [x] Nenhum motor paralelo foi criado (ledger = `billing_sent_log`; porta = `send_to_client_guarded`; sem fila, scheduler, sender ou inbox novos).
- [x] Nenhuma migration existente foi movida, renomeada, apagada ou reaplicada (2 novas: `20260907_01`, `20260907_02`).
- [x] Nenhum DDL monolítico foi aplicado.
- [x] Nenhum segredo foi exposto (telefones de teste só por alias; `to_phone` do ledger é dado da própria corretora e não aparece em log/relatório).
- [x] Nenhum escopo foi reduzido sem decisão registrada (o que saiu está na SPEC §11 com gatilho).
- [x] Nenhum dado atravessou tenants (G18 com dois tenants; red team ataque 2 resistiu; VERIFY V4e recusou o outro tenant no RPC).
- [x] `CLAUDE.md`, protocolo, glossário, decisão do ritmo, proposta e research pack lidos no início.

## 0.1 O PROTOCOLO AAA — as duas contas, a referência e o laço

| unidade | ALC | REV | FREQ | RISCO | SUP | piso? | time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| U1 motor + porta + migration | 3 | 3 | 2 | 8 | 3 | §3.2 envia + migration | desenhista · builder A · verificador · painel · juiz fresco |
| U2 respostas / convivência | 3 | 2 | 2 | 7 | 2 | §3.2 (toca o webhook do atendimento) | builder B · painel |
| U3 tela e rotas Next | 2 | 2 | 1 | 5 | 2 | herda o piso do lote | builder C · verificador · painel |
| U4 guardas · U5 canário · U6 docs | 0 | 0 | 0 | 0 | 1 | — | desenhista · orquestrador |

**Telemetria (§11):**
```
começou / terminou ............... 07/09/2026 ≈00:30 → ≈08:30 (limite de sessão) · retomada ≈09:40 → ≈10:40 · tempo até a 1ª linha de código de produto ≈ 2h40 (conversão + aquecimento)
rodadas de painel ................ 1 (3 lentes) + 1 juiz fresco · achados: verdade 2 B + 7 P · produto+DADO 1 B + 8 P · red team 1 B + 7 P · ÚNICOS: 4 blockers (B1 achado por 2 lentes) · juiz 2 B + 3 P
defeitos que o painel NÃO pegou .. 2: a regressão em `test_098_builder_b_unit` (o dublê da 098 com a assinatura antiga — pego pela SUÍTE inteira, triado contra a base) e
                                   a asserção migrada de `test_a_cobranca_alcanca_todas_as_seguradoras` (pego pela 2ª suíte)
rodadas da bateria ............... 📊 diário: 14 rodadas em 07/09, 2 inteiras (52 min + 19 min) · parciais: guarda do lote 9×, vizinhos 12× · ≈ 1h35 esperando a suíte
nota 0–100 do orquestrador ....... 87 — produto certo e conservador em cada bifurcação, 22/22 mutações vermelhas, 2 migrations verificadas no Postgres real, painel + juiz
                                   sem defeito de produto restante; perde por a prova VIVA ainda depender do Implantar e por duas horas de edição refeitas (a suíte
                                   restaura arquivos por cópia — lição registrada)
```

**RP0 (integridade dos insumos):** research pack `3ce221c0dca9600d0bcd5b568866e0c42d50b6ef0c2695f4d202a7a106d9a911` ✅ igual ao declarado na proposta. Proposta: entrada `e62b12bd71d3c6c4…` → cópia canônica sanitizada `5d23fc3d636bd1ae…` (telefones → aliases; cabeçalho registra a transformação). Prompt: `12ff4737…` → `39b61d27…`. LEIA-ME `ac6b6dcb…` sem alteração. Manifesto SHA-256 não veio no pacote; a prova é o hash cruzado da proposta.

**Aquecimento (Opus 5, contexto limpo, 07/09/2026, 📊 138.341 tokens · 34 tool uses · 6m52s):** nota **86**; as duas afirmações falsas assinadas foram refutadas pelo comando (`test_send_number` devolve `""` fora de `test` → `_send_test_messages` retorna `[]`; o entrelaçamento leitura `:1027` → envio `:1067` → gravação `:1105`); 11 emendas, todas aplicadas na SPEC v1.1 §0.5. **Dois defeitos materiais que a minha SPEC não via:** (1) `registrar_retorno` estava proposto dentro do background, mas `webhook.py:1366-1372` faz `observer_tap` **no endpoint** e retorna antes — com observador + agente desligado (= a Resulta hoje) o hook nunca rodaria; migrou para o endpoint, G24/M15 nascem; (2) a reserva por `ignore_duplicates` do PostgREST não infere índice único parcial (42P10 / 23505 estourado) — virou função no banco (`billing_reservar_obrigacao`), G25/M16 nascem. Também: `avisar_suporte_humano` não recebia `cfg` (3 chamadas; 📊 2 grupos `…@g.us` ativos) → parâmetro `suprimir` + G26; atendente excluída do contexto (G27); `incerto` não liberável; `portal_key` vazio retido; um telefone de teste real como placeholder em `PainelDeRotinas.tsx:861` (PII no repo) → máscara. O card do aquecimento pediu SUPERFÍCIE 4 (não existe na escala; mantido 3 com o 6º hub `observer_intake.py` anotado) e faixa 10–13 h (aceita: faixa passa a **8–13 h**).

**O laço (§5):**

| unidade | voltas | porta de saída | juiz da volta 3 |
|---|:---:|---|---|
| lote (U1–U5) | 2 (painel → conserto → juiz fresco → conserto de guarda) | liberou com pendências | — (juiz fresco confirmou; 2ª rodada foi de GUARDA, não de produto) |

**Blockers rebaixados a pendência pelo orquestrador (§4):** nenhum. Os 4 blockers do painel e os 2 do juiz foram consertados; as pendências P-J1/P-J3 (botão inútil; reserva órfã) também foram consertadas em `0be100a` por serem ≤ 30 min e ≤ 2 arquivos (§9).

**Blockers rebaixados a pendência:** (tabela vazia = nenhum)

**As pendências que esta SPEC TOCOU (§1):**

| P-nnn | estado |
|---|---|
| P-098-FILA-SEM-EXPIRE | CONTINUA — a cobrança deixou de usar a fila (`enfileirar=False`); a entrada continua sem TTL para os outros chamadores (099) |
| P-098-RUN-NOS-JOBS | PARCIAL — o run viaja da ponte (`bridge_rotina`) até o ledger e a porta na cobrança; os outros 3 chamadores continuam (099) |
| P-098-FICHA-RMW | CONTINUA — não tocada |
| P-097-TELEFONE-BR-DUPLICADO | PARCIAL — `billing_replies`, a porta (allowlist) e o ledger usam `telefone_br`; `channel_security._variants` e `_phone_variants` continuam copiando |
| P-098-UNIT-B-NA-SUITE | CONTINUA — 📊 48 errors dentro da suíte, 80/80 isolado (2× medido hoje) |
| P-098-FIXTURE-NOT-NULL | PARCIAL — `schema_vivo.json` ganhou `detalhe[tabela][coluna]={tipo,nulo,default}` para 24 tabelas; o dublê do guarda novo lê dali |
| P-098-APROVACAO-REIMPLEMENTA-O-GATE | CONTINUA — `approval` virou legado retido; `_create_approval_request` fica sem chamador até a volta |

---

## 1. Resumo executivo

A corretora passa a escolher, na tela do Auxiliar de Cobrança, entre **Encaminhar para minha equipe** (a atendente recebe uma nota interna, o texto final limpo e o PDF, e repassa ao cliente) e **Enviar diretamente ao cliente** (o segurado recebe texto limpo + PDF pelo WhatsApp já pareado da corretora). Antes desta SPEC, "enviar ao cliente" era uma frase no relatório (📊 `billing_collection.py:1734-1737` em `34424fa`) e o modo de aprovação criava um pedido que ninguém consumia.

Cada parcela é cobrada **uma vez**: a obrigação `(corretora, seguradora, recibo)` é **reservada no banco antes do efeito** por uma função Postgres (o índice único parcial não é inferido pelo PostgREST — achado do aquecimento), o estado é registrado por componente (texto/PDF), "incerto" nunca é repetido às cegas, trocar de modo ou de dia não reabre a cobrança, e um recibo igual ao de outra seguradora é **retido** com incidente em vez de virar "já cobrado". A porta única do WhatsApp ganhou conexão fixada e revalidada no instante do efeito, autorização de Auxiliar independente do interruptor do atendimento, documento, e uma allowlist de canário que exige remetente **e** destinatário autorizados.

O cliente que responde é ouvido **mesmo com o agente de atendimento desligado** (📊 4/4 hoje): o retorno é registrado no endpoint do webhook, antes de o observador consumir, e vira pendência na tela; o atendimento (quando ligado) recebe o bloco do caso em vez de uma nota genérica. A atendente **não** é interlocutor — nem para ler o caso, nem para encerrá-lo (o blocker que as duas lentes acharam e o conserto fechou com par de guarda). Observador, QR, sessões e o modo teste de 17/08 não mudaram (34/34 byte a byte).

**Ficou de fora, com gatilho:** e-mail/Meta/segundo QR (099), reenvio automático de 2ª via a pedido do cliente (tarefa da equipe), régua de lembretes, resposta automática viva no canário (caixa do Founder). **Não comprovado ao vivo ainda:** Q1–Q6 do canário e o 23505 concorrente no Postgres — só rodam dentro do smith-api implantado (sem Redis o governador recusa mensagem fria, e isso está certo).

## 2. Escopo executado por bloco

### U1 — motor, porta e migration
| Entrega prevista | Estado | Evidência |
|---|---|---|
| modos `equipe`/`cliente` com motor; `approval`/`live` retidos | CONCLUÍDA | `normalize_billing_config`, `_entregar_cobranca_real`; [G02] + M2 |
| pacote humano limpo (nota interna + texto final + PDF) | CONCLUÍDA | `_pacote_humano`; [G03] + M3 |
| ledger com estados por componente e reserva antes do efeito | CONCLUÍDA | migration `20260907_01` aplicada, `billing_reservar_obrigacao`; [G06]–[G11], [G19]; VERIFY §4 |
| porta com conexão fixada, autorização de auxiliar, documento, `enfileirar=False`, allowlist | CONCLUÍDA | `send_to_client_guarded`; [G01], [G12] + M1, M12 |
| aviso ao grupo suprimido no canário; incidentes em Atividades | CONCLUÍDA | [G17], [G26] + M18 |
| `work_run_id` da ponte até o ledger | PARCIAL (P-098-RUN-NOS-JOBS) | `routine_engine`, `workflows.bridge_rotina` |

### U2 — respostas e convivência
| Entrega prevista | Estado | Evidência |
|---|---|---|
| bloco do caso no atendimento, atendente excluída | CONCLUÍDA | `contexto_de_cobranca`; [G13], [G27] + M13, M19 |
| retorno registrado no ENDPOINT antes do observador | CONCLUÍDA | `registrar_retorno` + hook; [G24] + M15; corpus 43/43 [G14] |
| a atendente não encerra o caso (conserto do painel) | CONCLUÍDA | [G28] em par + M21 |
| takeover/URA intactos | CONCLUÍDA | [G15] diff vazio em `o_fim_do_atendimento.py`; [G16] |

### U3 — tela e rotas Next
| Entrega prevista | Estado | Evidência |
|---|---|---|
| 4 modalidades, `team_number`, confirmação, legado retido, placeholders mascarados | CONCLUÍDA | `PainelDeRotinas.tsx`; mjs verde; `tsc` |
| rotas `pendencias`/`encaminhado`/`liberar` com 401/404/409/400 | CONCLUÍDA | mjs [G18]; `next start` + requisição real (§5) |

### U4 — guardas · U5 — canário · U6 — docs
| Entrega prevista | Estado | Evidência |
|---|---|---|
| gate zero vermelho em cópia limpa; mutações por nome | CONCLUÍDA | 32 vermelhos em `50d2b4e`; `--mutar` (§5) |
| canário Q1–Q6 | ESCRITO, NÃO RODADO AO VIVO | `canario_extra001.py`; censo `--dry-run` verde; rota admin; depende do Implantar (§6) |
| EXTRA reconhecida pela polícia do protocolo | CONCLUÍDA | `test_o_protocolo_tem_policia.py` com controle |
| SPEC, relatório, INDICE, ESTADO, FOUNDER-DECISIONS, CHANGE-ADDENDA, PENDENCIAS, dossiê | CONCLUÍDA | commits §3 |

**Entregas da SPEC que NÃO foram executadas:** nenhuma da §2 obrigatória. A prova viva (canário) ficou dependente do Implantar, com o motivo medido (Redis) e o mecanismo pronto.

## 3. Arquivos alterados

```text
📊 git diff --stat 34424fa..0be100a: 46 files changed, ≈12.100 insertions(+), ≈120 deletions(-) · 17 commits
   produto (backend/app + app + components + scripts): 17 arquivos, ≈3.500 linhas
   testes (backend/tests + corpus + fixture): 5 arquivos, ≈5.900 linhas
   migrations: 3 arquivos (2 .sql + MANIFEST), ≈530 linhas
   docs: 20 arquivos, ≈2.200 linhas
```

| Área | Criados | Alterados | Removidos |
|---|---:|---:|---:|
| Backend | 4 (`billing_replies.py`, `canario_extra001.py`, `admin_canario.py`, `scripts/canario_extra001.py`) | 7 (`billing_collection.py`, `platform_outbound.py`, `webhook.py`, `billing_avisos.py`, `routine_engine.py`, `workflows.py`, `main.py`) | 0 |
| Frontend | 3 rotas (`pendencias`, `encaminhado`, `liberar`) | 2 (`PainelDeRotinas.tsx`, `rotinas/route.ts`) | 0 |
| Migrations | 2 (`20260907_01`, `20260907_02`) | 1 (`MANIFEST.md`) | 0 |
| Testes | 3 (`test_a_cobranca_chega_a_quem_deve.py`, `a-cobranca-chega-a-quem-deve.test.mjs`, `corpus/retornos_de_cobranca.json`) | 4 (`schema_vivo.json`, `test_o_protocolo_tem_policia.py`, `test_spec023_cobranca.py`, `rotina-mora-no-auxiliar.test.mjs`) | 0 |
| Documentação | 11 (SPEC, relatório, 6 pacotes, roteiro, proposta/RP/LEIA-ME/prompt instalados) | 8 (INDICE, ESTADO, FOUNDER-DECISIONS, CHANGE-ADDENDA, PENDENCIAS, dossiê, …) | 1 (`PROMPT-…EXTRA-001-PREENCHIDO.TXT` → `.md` sanitizado) |

## 4. Migrations

### `20260907_01_spec_extra001_billing_sent_log_estados.sql`

| Campo | Conteúdo |
|---|---|
| **Objetivo** | `billing_sent_log` ganha estado por componente, identidade da obrigação `(company_id, portal_key, recibo)` para os modos reais e as funções de reserva/reclamação atômicas |
| **Expand-first** | sim — 20 `ADD COLUMN IF NOT EXISTS` (todas nulas ou com default), 2 índices parciais `IF NOT EXISTS`, 2 `CREATE OR REPLACE FUNCTION`; nenhum DROP, nenhum backfill |
| **Destrutiva** | não |
| **APPLY** | aplicada em produção em 07/09/2026 via MCP `apply_migration` (`spec_extra001_billing_sent_log_estados`) → `{"success":true}`; o texto aplicado é o do arquivo canônico (com o ajuste `colisao_recibo` já dentro) |
| **VERIFY** | 📊 07/09/2026 · V1 `count(*)` das 20 colunas = **20** · V2 `pg_indexes` = **2** linhas, ambas `WHERE (send_mode = 'real'::text)` · V3 `pg_proc` = **2** funções com a assinatura do contrato · V4 contra o **Postgres real**, tenant Resulta, `canario=true`: 1ª reserva `ganhou=true, status=reservado`; 2ª (mesma obrigação, modalidade diferente) `ganhou=false`, **mesmo id**; 3ª (outro `portal_key`, mesmo recibo) `ganhou=false, status=colisao_recibo`; `billing_reclamar_obrigacao` a partir de `reservado` → **false**; com `company_id` de outro tenant → **false**; a linha do VERIFY apagada por `id + company_id + canario + recibo` (1 linha) · V5 controle `count(*) where send_mode='test'` = **0** antes e depois |
| **ROLLBACK** | escrito no cabeçalho do arquivo: `DROP FUNCTION ×2` → `DROP INDEX ×2` → `DROP COLUMN ×20`; seguro enquanto não houver linha `send_mode='real'` (📊 0 hoje); mensagens já enviadas não se desfazem |
| **Aplicada em produção** | sim · 07/09/2026 · versão registrada pelo MCP |
| **MANIFEST atualizado** | sim (linha da U1; classe passa de ⏳ para APLICADA neste relatório) |

**Advisors antes:** 📊 security 133 (2 ERROR · 9 WARN · 122 INFO)
**Advisors depois:** 📊 security 133 (2 ERROR · 9 WARN · 122 INFO)
**Diferença:** nenhuma. As duas funções novas declaram `SET search_path = public, pg_temp` — não entram no `function_search_path_mutable` (que continua listando só os 3 triggers antigos).

## 5. Testes executados

### 5.1 Obrigatórios

| Teste | Comando | Resultado | Saída |
|---|---|---|---|
| Isolamento multi-tenant (2 tenants) | `python tests/test_a_cobranca_chega_a_quem_deve.py` [G18] · red team ataque 2 · VERIFY V4e | PASS | leitura/claim/retorno não cruzam; RPC com outro tenant → `false`; rotas 404 |
| P0 de segurança | red team ataques 1, 2, 5, 12 | PASS | allowlist bilateral por variantes; conexão trocada → `conexao_trocada`; rota admin 401 sem chave |
| Idempotência de side effect | [G07]/[G08]/[G10]/[G19] · VERIFY V4a/V4b (Postgres real) | PASS | 2 execuções concorrentes → 1 PDF, 1 texto, 1 linha; `ganhou` true/false com o mesmo id |
| Migration incremental sobre estado atual | `apply_migration` ×2 + VERIFY | PASS | §4 |
| Migration em ambiente vazio | — | N/A | não há ambiente vazio (MIGRATIONS-AUTHORITY §6 pendente da 054); idempotente por `IF NOT EXISTS`/`OR REPLACE` |
| Approval / IDOR | rotas `encaminhado`/`liberar`: id de outro tenant → 404 (mjs) · G18 | PASS | |
| SSRF e egress | N/A | — | nenhuma URL nova consumida; o PDF é assinado no cofre da corretora |
| MCP env allowlist | N/A | — | não tocado |

### 5.2 Proporcionais ao risco desta SPEC

| Teste | Comando | Resultado |
|---|---|---|
| guarda do lote | `python tests/test_a_cobranca_chega_a_quem_deve.py` | 📊 **162 ok · 0 falhas · 3 pulados** ([G25] Postgres real ao vivo · [G18] rotas em execução · [G22]); gate zero em `50d2b4e`: **25 ok · 32 vermelhos** |
| mutações por nome | `--mutar` (worktree `-mut-e001`) | 📊 **22/22 vermelhas** (M1–M16 da SPEC + M17–M22 acrescentadas com motivo); 3 nasceram verdes e viraram conserto no guarda |
| modo teste intacto | `python tests/test_a_cobranca_esta_como_estava.py` | **34/34** (5 funções byte a byte iguais a `34424fa`, medido pela lente de verdade) |
| segurança da 078 | `python tests/test_spec078_bloco_a_seguranca.py` | **39/39** |
| cobrança em todas as seguradoras | `python tests/test_a_cobranca_alcanca_todas_as_seguradoras.py` | **171/171** (uma asserção migrou o fato no aviso do grupo) |
| spec023 | `python tests/test_spec023_cobranca.py` | **131/131** (uma asserção migrou: `live` é legado) |
| governador | `python tests/test_governador_de_envio.py` | verde |
| 098 unit (a porta) | `pytest tests/test_098_builder_b_unit.py` | **80/80** isolado (a chamada antiga de `_entregar_agora` foi preservada) |
| tela e rotas | `node scripts/a-cobranca-chega-a-quem-deve.test.mjs` · `rotina-mora-no-auxiliar.test.mjs` · `npx tsc --noEmit` | verdes |
| §9.1 o servidor responde | `npm run test:rotas-montam` (301) · `next build` (306 rotas) · `next start` + `GET pendencias` → **401** · `POST liberar` → **401** · `POST encaminhado` → **401** · controle `liberar-reenvio` → **401** | PASS |
| polícia do protocolo | `python tests/test_o_protocolo_tem_policia.py` | 📊 (colar ao fechar) |
| canário local | `scripts/canario_extra001.py --dry-run` | censo verde: conexão da Resulta = TESTE-A, destino = TESTE-B, os dois na allowlist |

### 5.3 Suíte inteira (2 rodadas, árvore parada) e triagem nominal

| rodada | resultado | triagem |
|---|---|---|
| 1ª (f3da63e) | 📊 1008 passed · 13 failed · 48 errors · 52m43 | 48 errors + 2 failed = P-098-UNIT-B-NA-SUITE (80/80 isolado); `test_o_protocolo_tem_policia` = relatório ainda aberto; `test_a_atendente_aperta_o_botao` (1 falha) e `test_ontologia_e_unica` (1 error) **falham igual na base `50d2b4e`**; `test_o_sinistro_deixa_rastro`, `test_r11_no_destilador` passam isolados na base e no HEAD (classe P-093B-HARNESS); 6 guardas-script + "árvore limpa" = harness (`test_todos_os_guardas_script_rodam`) e a árvore não estava parada (edição durante a suíte — a lição) |
| 2ª (f11f543) | 📊 1013 passed · 9 failed · 48 errors · 18m45 | mesmos pré-existentes; **1 regressão real** achada: `test_a_cobranca_alcanca_todas_as_seguradoras` 170/171 (o aviso do grupo) → consertado em `0be100a` (171/171); `test_sem_corredor_de_vidro_nao_e_beco` passa isolado no HEAD e na base |

**Regressões encontradas:** 2, ambas consertadas com prova (80/80 e 171/171) — nenhuma restante atribuível a esta SPEC.

## 6. Canário e rollout

### 6.1 Estado separado (proposta §18)

| marco | evidência exigida | estado |
|---|---|---|
| Implementado e gateado | commits `50d2b4e…` · guarda 155/155 · mutações · painel · juiz fresco | (preencher ao fechar) |
| Entregue na main | SHA remoto + saída do `git push` | (preencher §14) |
| Implantado | `code_fingerprint` do `/health` diferente de `9c8c9f09bd153538` (📊 07/09 antes do deploy) + `POST /api/admin/canario/extra001/plano` com chave respondendo 200 | **pendente do clique Implantar** (🧑) |
| Validado no canário autorizado | Q1–Q6 pela rota admin, com aliases | **pendente**: só roda no implantado (P-E001-CANARIO-VIVO-NO-IMPLANTADO). Censo local (`--dry-run`, 📊 07/09): conexão da Resulta = observer `connected`, remetente …4743 = TESTE-A, destino …7463 = TESTE-B, os dois na allowlist |
| Validado pelas pilotos | feedback de Saionara/Regina registrado pelo Founder | não iniciado — roteiro em `docs/canon/ROTEIRO-VALIDACAO-EXTRA-001-ATENDENTES.md` |
| Ativado em linhas operacionais | fora da autorização | **não realizado, não presumido** |

### 6.2 Ordem de implantação — medida, não copiada da 098

📊 `app/api/dashboard/rotinas/route.ts` novo grava `send_mode ∈ {equipe, cliente}`; o `normalize_billing_config` **antigo** (`billing_collection.py:403-405` em `34424fa`) devolve `test` para qualquer valor fora de `{test, approval, live, none}`. Web nova + API antiga = uma rotina salva como "Enviar ao cliente" executaria como **teste** (para o `test_number`, que pode estar vazio → nada sai, mas a tela mentiria). API nova + web antiga = a web só oferece `test/none`, a API entende os dois → inócuo.

**Ordem: smith-api PRIMEIRO, smith-web DEPOIS.** Sem migration pendente (já aplicada). Variáveis novas no smith-api (🧑): `BILLING_CANARIO_ALLOWLIST` (os dois números de teste, só dígitos com 55, separados por vírgula) e `CANARIO_TESTE_B` (o número que recebe). Nenhuma variável nova para a operação normal.

### 6.3 Canário (Q1–Q6) — preencher depois do Implantar

| Q | o que prova | resultado |
|---|---|---|
| Q1 | equipe: 3 mensagens em TESTE-B; ledger `entregue_equipe`, `canario=true` | pendente |
| Q2a/Q2b | cliente: 0 envios até liberar; depois texto + PDF | pendente |
| Q3 | reexecução: 0 envios | pendente |
| Q4 / Q4-vivo | retorno "já paguei" → `contestado` + atividade; a resposta REAL de TESTE-B pelo webhook | pendente |
| Q5 | destino fora da allowlist → `fora_da_allowlist`, 0 envios | pendente |
| Q6 | limpeza por id: ledger 0 · platform_sends 0 · atividades 0 · PDF removido | pendente |

**Flags criadas ou alteradas:** nenhuma flag de produto. `canario` é campo de config gravado só pelo script/rota do canário; a tela nunca o expõe.
**Auto-pause configurado:** o freio existente (`parar_envios`) continua valendo para a cobrança real (a porta consulta `envios_parados`).

## 7. Gate da SPEC

| Critério (SPEC §8) | Atendido | Evidência |
|---|---|---|
| G00 base/schema medidos | SIM | SPEC §1 (20 medições), censo do canário |
| G01 remetente E destinatário na allowlist | SIM (dublê) | [G01] + M1; red team ataque 1 (6 provas) |
| G02 4 modos distintos; legado retido | SIM | [G02] + M2; `confirmacao_cliente` por `_truthy` |
| G03 pacote humano limpo | SIM | [G03] + M3 |
| G04/G05 direto ao contato validado; PDF do item | SIM | [G04] + M4 · [G05] + M5 |
| G06 estado por componente | SIM | [G06] + M6 |
| G07 uma reserva vencedora | SIM (dublê + Postgres real no VERIFY) | [G07] + M7; V4a/V4b |
| G08 dia/run/modo não reenvia | SIM | [G08] + M8 |
| G09 falha de histórico bloqueia | SIM | [G09] + M9 |
| G10 timeout não repete | SIM | [G10] + M10 |
| G11 equipe→cliente respeita decisão | SIM | [G11] + M11 |
| G12 conexão trocada | SIM | [G12] + M12 |
| G13/G27 contexto do caso; atendente não herda | SIM | + M13, M19 |
| G14 já paguei/contestação/opt-out | SIM | corpus 43/43 + M14/M17 |
| G15/G16 takeover e URA intactos | SIM | diff vazio em `o_fim_do_atendimento.py`; [G16] |
| G17 falhas visíveis | SIM | `agent_activities` + motivos em português |
| G18 dois tenants | SIM | [G18] + M20; mjs; red team |
| G19 reinício | SIM | [G19]; reserva órfã com saída pela rota |
| G20 regressão | SIM | 34/34 · 39/39 · 171/171 · 131/131 · 80/80 · governador · rotas-montam · next start |
| G21 injeção | SIM | [G21]; recibo saneado |
| G22 instalação ≠ validação | SIM (documento) | §6.1 |
| G23 docs coerentes | SIM | polícia reconhece EXTRA; dossiê `#extra001` |
| G24 retorno com observador consumindo | SIM | [G24] + M15 |
| G25 reserva real no Postgres | PARCIAL | VERIFY V4 (sequencial, real); a corrida CONCORRENTE ao vivo só no canário implantado |
| G26 grupo suprimido | SIM | [G26] + M18 |
| G28/G28b a atendente não encerra o caso; o chamador cobre | SIM | + M21, M22 |
| Canário Q1–Q6 | **NÃO COMPROVADO AO VIVO** | escrito, censo verde; roda só no implantado (P-E001-CANARIO-VIVO-NO-IMPLANTADO) |

**Veredito do gate:** **VERDE COM RESSALVA** — a ressalva é a prova viva (Q1–Q6, G25 concorrente), que depende do clique Implantar e de duas variáveis; fecha nesta mesma SPEC assim que o Founder implantar (§6.3).

## 8. Mudanças além do texto da SPEC

| ID em `CHANGE-ADDENDA.md` | Classe | Estado | Resumo |
|---|---|---|---|
| 07/09 · peça da Cobrança nunca publicada | ESSENCIAL | feita | `NameError` engolido desde a 095; consertado em U1 |
| 07/09 · rota admin do canário | ESSENCIAL | feita | o canário vivo roda onde há Redis, atrás da chave interna |
| 07/09 · EXTRA na polícia do protocolo | ESSENCIAL | feita | `SPEC-EXTRA-NNN` → sob a v11 |
| 07/09 · colisão de recibo | ESSENCIAL | feita | `colisao_recibo` retido com incidente; migration 02 devolve id NULL |
| 07/09 · telefones reais como placeholder | ESSENCIAL | feita | máscara na tela; guarda mjs |
| 07/09 · guardas vizinhos migraram o fato | VALIOSA | feita | `rotina-mora-no-auxiliar`, `test_spec023` |

## 9. Decisões registradas

| ID em `FOUNDER-DECISIONS.md` | Assunto | Estado |
|---|---|---|
| D-E001-01…10 | as decisões do Founder que governam a EXTRA-001 | registradas 07/09 |
| (caixa) | ligar o agente da Resulta por uma janela para a resposta viva | não decidido |

## 10. Riscos remanescentes e dívida assumida

| Risco | Severidade | Por que foi aceito | Onde será fechado |
|---|---|---|---|
| Q1–Q6 e o 23505 concorrente ainda não provados ao vivo | alta (é a prova do produto) | só rodam no implantado; mecanismo pronto (rota admin) | depois do Implantar, nesta mesma SPEC (caixa do Founder) |
| `incerto` depende de uma 2ª escrita que pode falhar pelo mesmo motivo | média | `reservado` também nunca é reclamado e aparece no relatório | P-E001-INCERTO-ESCRITA-DUPLA |
| hook do retorno no caminho quente de todo inbound (teto 2 s) | média | 1 SELECT por mensagem; falha nunca derruba o atendimento | P-E001-ROUTINES-POR-INBOUND (cache) |
| a constraint antiga `(company_id, recibo, send_mode)` continua não-parcial | baixa | colisão vira retenção com incidente, nunca silêncio | migration futura que a torne parcial (099) |
| `status='entregue'` legado não vira `contestado` | baixa | 📊 0 linhas legadas | P-E001-LEGADO-ENTREGUE-NAO-CONTESTA |
| ledger sem vencimento/valor | baixa | o bloco diz que não tem | P-E001-LEDGER-SEM-VENCIMENTO-E-VALOR |

## 11. Impacto para o corretor

Hoje a corretora consegue: escolher se o boleto atrasado vai para a **equipe** (pacote pronto para repassar, com uma nota dizendo de quem é) ou **direto para o cliente**; saber que **nenhum cliente recebe a mesma parcela duas vezes** (nem trocando de modo, nem no dia seguinte, nem com duas execuções ao mesmo tempo); ver na tela **o que ficou pendente e por quê** em português (texto foi e PDF não; não sei se saiu; cliente respondeu "já paguei"; cliente pediu para não receber); marcar "encaminhado ao cliente" e "liberar reenvio" com motivo; e ser avisada quando um cliente responde à cobrança, mesmo com o agente de atendimento desligado. O grupo de suporte deixa de ler "enviado" quando o boleto foi para a própria equipe.

O que ainda **não** vê: a prova viva de ponta a ponta (depende do Implantar + duas variáveis + o clique na rota do canário) e a resposta automática ao cliente (depende de ligar o agente).

## 12. Estado do Master Plan

- [x] `INDICE-DE-SPECS.md` e `ESTADO-DAS-SPECS.md`: EXTRA-001 em execução; 099→114 pausadas sem renumerar.
- [x] `FOUNDER-DECISIONS.md`: D-E001-01…10.
- [x] `CHANGE-ADDENDA.md`: 6 adendas.
- [x] `MANIFEST.md`: migrations 20260907_01 e 20260907_02 (aplicadas).
- [x] `PENDENCIAS.md`: 12 P-E001-*.

**Próxima etapa do plano:** EXTRA-002 · investigação Agger (proposta a escrever em chat novo). Depois 099 (canais, após os pilotos).
**Pré-condições:** Implantar esta SPEC; canário Q1–Q6 verde no implantado; roteiro com Saionara/Regina conduzido pelo Founder.

## 13. ROLLBACK da SPEC inteira

```text
1. aplicação: reverter os commits da branch (git revert em ordem inversa); a API antiga normaliza equipe/cliente para 'test' —
   uma rotina configurada em modo real passaria a rodar como TESTE (para o test_number), então antes de reverter, pôr as rotinas
   de cobrança em 'none'.
2. flags: nenhuma. Retirar BILLING_CANARIO_ALLOWLIST e CANARIO_TESTE_B do smith-api.
3. banco: ROLLBACK das migrations 20260907_02 (reaplicar os corpos da 01) e 20260907_01 (DROP FUNCTION ×2, DROP INDEX ×2,
   DROP COLUMN ×20) — só seguro sem linhas send_mode='real' (📊 0 hoje).
4. side effects já executados: mensagens enviadas não se desfazem; o ledger fica (é a prova de que saíram).
5. o que NÃO é reversível: as mensagens do canário (TESTE-A → TESTE-B) e as linhas de agent_activities do período.
```

## 14. A entrega (`git push`) — saída colada

```
$ git fetch origin; git rev-list --count HEAD..origin/main   → 0 (atrás)
$ git rev-list --count origin/main..HEAD                     → 18 (à frente)
$ git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   34424fa..ba7ba75  HEAD -> main
$ git fetch origin && git rev-parse --short origin/main      → ba7ba75
$ git rev-list --count origin/main..HEAD                     → 0
```

📊 07/09/2026. A `main` remota está em `ba7ba75` (código em `0be100a` + o relatório). O commit do dossiê/§14 vem em seguida e é empurrado do mesmo jeito. **Implantar** é do Founder (EasyPanel): **smith-api primeiro, smith-web depois** (§6.2), e as duas variáveis do canário no smith-api.

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC

📊 `backend/.diario-da-bateria.jsonl`, entradas de 07/09/2026 (o comando do template, filtrado pelo dia):

| | |
|---|---|
| rodadas no total | **16** |
| das quais bateria inteira | **2** (52m43 em `f3da63e` · 18m45 em `f11f543`) |
| **relógio total esperando a suíte** | **≈ 77 min** (≈ 71 min nas inteiras) |
| **fração da execução** | ≈ 9 % das ≈ 14 h |

📊 bateria: 16 rodadas, 2 inteiras. nota da execução: 87/100 (§0.1).
