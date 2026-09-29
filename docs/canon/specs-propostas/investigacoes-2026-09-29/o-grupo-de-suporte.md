# Investigação — o grupo de suporte recebe avisos que não deveria (só leitura)

Árvore `AutoBrokers-FIX`, HEAD `c310e77` (origin/main `1fb9db1`, 0 atrás). Banco: `SUPABASE_DB_URL` com `SET TRANSACTION READ ONLY`. Nenhuma mensagem enviada, nada gravado, repositório intocado. Consultas em `inv-grupo/q.py`, `classif.sql` e `armadas.sql`. As corretoras aparecem como **C1** = `04b5cdbc…` e **C2** = `6c9c55e2…`. As conversas aparecem pelo prefixo do uuid.

## 0. Em uma frase
📊 **29 de 29** avisos que saíram ao grupo desde que a porta única existe (16/09) falavam de conversas que a atendente **já tinha atendido pelo celular** e que o agente **nunca pediu**. Todos saíram com o agente de atendimento **desligado**. Avisos legítimos: **0**. A regra do Founder está correta nos dados.

A causa tem três partes:
1. O vigia lê `status='HUMAN_REQUESTED'` como "o agente pediu ajuda". Só que quem grava esse status, na prática, é o espelho, quando **a atendente responde**.
2. A porta do grupo **não pergunta** se o agente está ligado.
3. A proteção "um humano já falou" vence em **6 h** (pelo claim) ou em **7 dias** (pela janela, que só enxerga as últimas 40 mensagens). Depois disso, a porta deixa passar.

A SPEC-120 fecha o lembrete repetido. **Não fecha** as três partes acima.

## 1. Mapa do código

**A porta:** `o_grupo_so_o_que_importa.py:641` `enviar_ao_grupo` chama a guarda `o_grupo_pode_saber` (`:332`). A guarda faz estas perguntas, nesta ordem:
- ① o tipo é isento? `sinistro`, `conclusao`, `resumo_diario` e `queda_de_canal` passam sem mais nada (`:85`);
- 1-bis) a pausa humana de 15 s está aberta? (`:375`);
- ② o número é da própria corretora? (`:380`);
- ③ há claim com menos de `HANDOFF_REALERTA_HORAS`=6 h? (`:520`);
- ④ um humano falou nos últimos N dias? (`:445`).

⛔ **Em nenhum ponto do módulo se consulta `attendance_agent_active`** (`atlas/attendance_capture.py:296`). E a guarda é **fail-open**: se não consegue ler, deixa passar (`:415`, `:440`, `:455`).

**Como a guarda decide que "o humano falou" (pergunta ④):** usa `o_fim_do_atendimento.ultima_palavra_humana` (`:1305`). Conta como palavra humana uma mensagem `role='assistant'` com `payload.origem` igual a `espelho` (celular pareado, `fromMe`) ou a `dashboard`, descontados o eco do agente e as `#nota`. ⚠️ Ela só olha as **últimas 40 linhas** (`_MENSAGENS_DA_JANELA`, `:1129`).
- A janela de 7 dias vive em `JANELA_SILENCIO_HUMANO_DIAS = 7` (`o_fim_do_atendimento.py:1104`). Pode ser trocada pela env ou por `acionamento_profile.janela_silencio_humano_dias`. 📊 Nenhuma das duas corretoras tem override, e a env não está no `.env`.
- A janela de 15 s vive em `PAUSA_HUMANA_S = 15` (`insurer_dispatch_service.py:560`). Ela cobre **a atendente falando na URA da seguradora**: com 1 fala o robô espera 15 s; com 2 falas ele sai. A guarda do grupo respeita essa pausa (`:375`). ⚠️ Não encontrei uma janela de 15 s disparada por **clique** de "destravar" no painel. O que existe é o botão "Devolver ao agente".
- O "humano assumiu" **não depende de clique**. 📊 Nas 470 conversas `HUMAN_REQUESTED`, o `claimed_by` está NULL em todas, e `claimed_by_name='Atendente pelo celular'` aparece em todas. Quem escreve isso é `espelho_chat.pausar_por_intervencao_humana` (`:711`, update em `:762`), a cada vez que a atendente escreve pelo celular pareado. Se ela usa **outro aparelho**, nenhum sinal chega. É um limite declarado.

| remetente | arquivo:linha | tipo | checa agente ligado? | checa humano? |
|---|---|---|---|---|
| pedido do agente (`_arun` → `_avisar_suporte`) | `human_handoff.py:1425` → `:1193` | pedido_de_ajuda / **sinistro (isento)** | indireto (só roda num turno do agente, que o webhook barra em `webhook.py:1442/1490`) | porta ③④; **sinistro passa direto** |
| **vigia: aviso tardio** | `handoff_watchdog.py:288` | pedido_de_ajuda | **NÃO** | porta ③④ + "a última palavra é do cliente?" (`:189-205`, fail-open) |
| vigia: espera vencida | `handoff_watchdog.py:564` | espera_vencida | **NÃO** | porta ③④ |
| dossiê do acionamento | `dispatch_router.py:4464` | pedido_de_ajuda (com `sessao`) | indireto (o acionamento exige agente ligado) | porta 1-bis③④ |
| protocolo não chegou | `dispatch_router.py:196` | vigia | **NÃO** | porta |
| retomada | `dispatch_router.py:2948` | retomada | **NÃO** | porta |
| Vigia do acionamento | `dispatch_watchdog.py:428` | vigia | **NÃO** | porta 1-bis③④ |
| conclusão ✅ | `o_fim_do_atendimento.py:422` | conclusao (**isento**) | não | **nenhum** |
| lacuna de conhecimento | `lacunas_de_conhecimento.py:400` | pedido_de_ajuda | indireto (turno do agente) | porta |
| resumo das 19h | `o_resumo_das_19h.py:142` | resumo_diario (isento) | **SIM** (`:111`) | não se aplica |
| fila longa | `aviso_de_fila_longa.py:255` | espera_vencida, sem conversa | não (flag desligada) | não se aplica |
| cobrança (auxiliar) | `billing_collection.py:284` | cobranca, sem conversa | não precisa | não se aplica |
| sentinela de regressão (auxiliar) | `regression_sentinel.py:102` | vigia, sem conversa | não precisa | não se aplica |
| teste manual do admin | `admin_spec034.py:232` | **fora da porta** | — | — |

## 2. Evidência no banco

📊 `work_events` com `grupo.enviado`/`grupo.calado` nos últimos 60 dias (29/09/2026):

| corretora | enviado | calado |
|---|---|---|
| C1 | 14 pedido_de_ajuda (21/09) | 0 |
| C2 | 14 pedido_de_ajuda + 1 sinistro (21/09) | 7 (17–18/09, "a atendente falou há 6 dias") |

- `platform_sends` com `kind like 'grupo_%'` bate 1:1 (14 / 14+1).
- Os mesmos 29 aparecem como `handoff.realertado`, o que **prova que o remetente foi o vigia** (`varrer_handoffs_parados`). Nenhum veio do pedido do agente.
- Antes de 16/09 não existe registro por conversa. Existem 5 "Dossiê entregue à equipe" (C1, de 18/08 a 10/09) e o incidente de 10/09 (7 avisos em 75,7 min, 6 deles depois de a atendente ter digitado na URA). Esse incidente está documentado em `o_grupo_so_o_que_importa.py:3-18`.

**A classificação dos 29** (query em `classif.sql`, com junção por prefixo de conversa e `company_id`):

📊 **(a) A atendente já conhecia: 29/29.**
- 29/29 são conversas **nascidas do espelho** (`agent_id IS NULL`).
- Em 29/29 existe mensagem `origem='espelho'` de saída **antes** do aviso, entre **241,6 h e 295,7 h** antes.
- Em **27/29** a última mensagem era **dela**: ninguém estava esperando.
- Em **25/29** o agente tem **0 falas** na conversa.
- 28/29 não têm `human_handoff_reason`. O dossiê inventou *"o segurado pediu para falar com uma pessoa"* (`handoff_watchdog.py:285`).

📊 **(b) Agente desligado: 29/29.**
- `agents` com `agent_role='attendance'` e `is_active=false` nas duas corretoras; `updated_at` em 09/09 14:46 e 10/09 17:54.
- Nenhuma fala do agente em conversa de WhatsApp depois de 10/09. As 10 falas de 17/09, 21/09 e 26/09 são `channel='web'` (o painel).
- ⚠️ Ressalva: a tabela `agents` não tem trigger de `updated_at`, então a prova é por ausência de fala. É uma INFERÊNCIA forte.

📊 **(c) Legítimo: 0.**

**Exemplos mascarados:**
- `4ba108d1` (C2): o segurado escreveu em 09/09 às 14:18, a atendente respondeu às 14:25 e ficou com a última palavra. Aviso em 21/09 às 22:04, **295,7 h depois**.
- `9ba104aa` (C2): a atendente respondeu em 10/09 às 12:58. Aviso 273,1 h depois. 0 falas do agente.
- `b106df72` (C1): a atendente fez a última fala, de 229 caracteres, em 10/09 às 20:07. Aviso 266,0 h depois.
- `90f62394` (C1): a atendente falou em 11/09 às 18:56, o segurado respondeu às 19:27, e depois veio o silêncio. Aviso em 21/09 às 17:03 (238,1 h). É o caso de "cliente por último", e mesmo assim a atendente conhecia a conversa.
- `dc54572a` (C2, **sinistro**): a atendente falou em 10/09 às 18:48. Saiu porque sinistro é **isento** da guarda.

📊 **O que ainda está exposto hoje** (`armadas.sql`):

| | C1 | C2 |
|---|---|---|
| conversas `HUMAN_REQUESTED` | 191 | 279 |
| delas, nascidas do espelho | **191** | **279** |
| atendente falou há mais de 7 dias | 111 | 130 |
| o cliente foi o último a falar e está fora da janela | **63** | **32** |

Para as 95 da última linha, basta uma mensagem nova do segurado para o vigia pós-SPEC-120 mandar o "primeiro aviso" entre 30 min e 2 h depois. Hoje isso não acontece só porque `human_support_destinations.is_active=false` (as duas desativadas em 21/09, às 22:43 e 22:46). ⚠️ Nesse estado, a porta **não deixa rastro**: `_NaoSaiu` volta antes do diário (`:739-744`).

📊 Existem 653 (C1) e 565 (C2) eventos `handoff.teto_de_lembretes` até **29/09 às 12:00 UTC**. O HEAD atual não escreve esse evento. INFERÊNCIA: **a SPEC-120 ainda não estava no ar** nessa hora.

## 3. As causas

**Causa 1, classe (a): `HUMAN_REQUESTED` tem dois sentidos opostos, e o vigia usa o errado.**
- O espelho grava `HUMAN_REQUESTED` quando a atendente responde (`espelho_chat.py:762`).
- O vigia varre `HUMAN_REQUESTED` como se fosse um pedido do agente (`handoff_watchdog.py:151`) e chama `_avisar_suporte` com motivo inventado (`:285-289`).
- A SPEC-120 manteve o "aviso tardio" (`0e1ffb0`/`bf18e8f`): ele ainda dispara para conversa de espelho em que o segurado voltou a escrever nas últimas 2 h.

**Causa 2, classe (a): a proteção vence.**
- Claim só vale por 6 h (`o_grupo_so_o_que_importa.py:520`, o mesmo P-120-14).
- A janela olha só 40 linhas (`o_fim_do_atendimento.py:1129`).
- No dia 8 a conversa passa a ser tratada como "nova". Pela regra do Founder, virar conversa nova autoriza o **agente** a atender. Não autoriza avisar o grupo de algo que o agente nunca tentou.
- E sinistro e conclusão são isentos (`:85`): passam mesmo quando a atendente está no meio da conversa.

**Causa 3, classe (a): o filtro "o cliente está esperando?" do vigia deixou passar 27 conversas em que a última palavra era da atendente.**
- Os dois caminhos do código que produzem isso são fail-open. Em `:189`, uma falha de leitura faz todas contarem como "esperando". Em `:205`, a conversa que não aparece no lote (limite de 1.000 linhas do PostgREST, com `limit(1500)` pedido em `:195`) cai no padrão `"user"`.
- 📊 Não consegui reproduzir qual dos dois aconteceu: numa simulação do lote de 21/09, 0 das alertadas estariam cortadas. **INFERÊNCIA não confirmada.**

**Causa 4, classe (b): nenhum remetente em segundo plano pergunta se o agente está ligado.**
- Vigia, espera vencida, dispatch_watchdog e retomada não perguntam, e a porta também não.
- Só o resumo das 19h faz essa checagem (`o_resumo_das_19h.py:111`).

**A SPEC-120 resolve?**
- **Parcialmente.** Tirou o lembrete de conversa antiga (D16): o disparo de 244 h de 21/09 não se repete.
- **Não resolve** as causas 1, 2 e 4, nem o isento de sinistro/conclusão.
- A frase *"com humano atendendo, nada sai ao grupo (D17)"* do relatório §1.3 só é verdade por 6 h pelo claim, ou por 7 dias e 40 linhas pela janela.

## 4. O conserto mínimo e seguro

**A regra única do ATENDIMENTO.** Vale para todo aviso que tem `conversation_id` de segurado. A porta avisa **somente se as três forem verdadeiras**:

```
A. o agente de atendimento está LIGADO agora     attendance_agent_active(company) — fail-closed
B. o AGENTE pediu esta conversa neste ciclo      o pedido nasceu de uma ação do agente
                                                 (human_handoff._arun, acionamento, espera criada
                                                 pelo agente), nunca de HUMAN_REQUESTED do espelho
C. NENHUM humano da corretora falou com o         qualquer um destes sinais, dentro de N=7 dias
   cliente nos últimos N dias                     (a MESMA janela_de_silencio_dias):
                                                 · mensagem origem espelho/dashboard (sem eco, sem #nota),
                                                   lida SEM o teto de 40 linhas (role='assistant' +
                                                   created_at >= agora−N, índice existente)
                                                 · claimed_by OU claimed_by_name com claimed_at ≤ N dias
                                                   (claim passa a valer N dias, não 6 h — fecha P-120-14)
                                                 · pausa humana da URA aberta (15 s, já existe)
```

Isto sai da lista de isentos para avisos **de conversa**: `sinistro` e `conclusao`. Eles continuam fora da deduplicação, mas obedecem A, B e C.

**Os auxiliares não mudam.** A regra só se aplica quando há `conversation_id`. Cobrança, sentinela de regressão, fila longa, queda de canal e resumo das 19h não passam conversa e continuam como estão. O resumo das 19h já exige o agente ligado.

**Onde mexer (mínimo):**
1. `o_grupo_pode_saber`: acrescentar a pergunta A logo no início (quando há conversa); estender o claim para N dias; ler a palavra humana sem o teto de 40; e, para tipos de atendimento, falhar **fechado**. Tudo gravado em `grupo.calado` com o motivo.
2. `handoff_watchdog.py:271-297`: o aviso tardio só roda com prova de que o agente pediu (`human_handoff_reason` não nulo **e** fala do agente depois da última palavra humana), ou é removido de vez. O padrão `"user"` em `:205` e o `set(ids)` em `:189` passam a significar "não avisar".
3. Registrar em `grupo.calado` também o `_NaoSaiu`, para o silêncio deixar rastro.

**As alternativas, com nota:**

| alternativa | nota |
|---|---|
| **A+B+C na porta, com o vigia exigindo pedido do agente** (acima) | **92** |
| só remover o aviso tardio do vigia + a pergunta A na porta | 84: é simples, mas deixa o furo do dia 8 no sinistro e na conclusão |
| só a pergunta "agente ligado" na porta | 58: fecha a classe (b) e deixa a (a) inteira quando o agente religar |
| trocar o status que o espelho grava (`HUMAN_ACTIVE`) | 55 agora: é o certo semanticamente, mas mexe em todos os leitores e exige migration; fica como FUTURA |
| fail-closed × fail-open para os tipos de atendimento | fechado **80** × aberto 55. O pedido continua na Fila do painel; avisar à toa é exatamente a queixa |

**Os testes, sempre com linha de CONTROLE, chamando o MOTOR** (`o_grupo_pode_saber` e `varrer_handoffs_parados`):
- **T1.** Agente desligado + pedido_de_ajuda deve dar **calado**. Controle: a mesma conversa com o agente ligado dá enviado. Segundo controle: cobrança e regressão com o agente desligado dão enviado.
- **T2.** Conversa de espelho em `HUMAN_REQUESTED`, atendente há 8 dias, cliente escreveu agora: o vigia **não chama** a porta. Controle: conversa em que `_arun` pediu ajuda e o aviso falhou: 1 envio.
- **T3.** A atendente falou há 3 dias e vieram 60 mensagens depois: **calado**. Controle: nenhuma fala humana dá enviado. Isto prova que o teto de 40 caiu.
- **T4.** Claim de 6,1 h sem mensagem humana: **calado**. Controle: claim de 7 dias e 1 h dá enviado.
- **T5.** Sinistro com a atendente tendo falado há 2 dias: **calado**. Controle: sinistro sem humano dá enviado.
- **T6.** A leitura falha: tipo de atendimento dá **calado**; controle: cobrança com a mesma falha dá enviado.
- **T7, a regressão de 21/09.** As 29 formas reais, anonimizadas, precisam dar **0 envios**. Cada mutação precisa ficar vermelha: tirar a pergunta A, voltar o claim para 6 h, voltar o teto de 40, devolver sinistro à lista de isentos.
- **T8.** O vigia com 50 conversas somando mais de 1.000 mensagens: nenhuma cortada vira "esperando".

**O que o Founder precisa confirmar:**
- (i) conclusão ✅ também cala quando a atendente participou (a regra literal dele diz "nunca");
- (ii) o aviso tardio sai de vez (nota 84) ou fica com a prova B (nota 92).

**Limites desta investigação:**
- Os grupos não são capturados no acervo: 📊 0 linhas `@g.us` em `attendance_transcripts`. A contagem vem do diário e do ledger, que só existem a partir de 16/09.
- A atendente que responde de um aparelho **não pareado** não é detectada por nenhum sinal.
