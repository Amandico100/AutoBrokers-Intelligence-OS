# SPEC-097.1 · O CASO SE EXPLICA SOZINHO — o pós-acionamento tem estado, o agente responde com ele, e o que sobra vai para humano dizendo que é PÓS

> **O que ela entrega:** depois que a atendente informa o acionamento (protocolo, prestador, previsão), o cliente volta — e hoje o produto tem
> **zero** nesse trecho: 📊 os dois agentes de atendimento estão `is_active=false` e os prompts (1,5 KB) só cobrem a ABERTURA; o Auxiliar
> `follow-up-whatsapp` não está instalado em nenhum tenant e não tem gatilho; `work_waits` tem 0 linhas na vida; `human_handoff_reason` é NULL em
> 725/729; o dossiê de handoff não tem título de pós-acionamento e o seu default diz *"conclua o acionamento"* para um caso já acionado.
> A 097.1 **preenche** o que a 097 construiu (`Caso`/`Agora`/`Espera`/`ProximaAcao`, estágios `protocolo`/`monitorando`/`esperando`/`parado`):
> (1) **o estado existe** — o corredor ESCREVE de quem se espera e desde quando (`work_waits`), no ponto em que o acionamento vira espera;
> (2) **o agente responde com regra e com estado** — seis cartas em linguagem de corretora (carro reserva, franquia, previsão, vistoria, documentos,
> prestador não chegou) e uma seção de pós-acionamento no prompt de atendimento que só afirma o que está ESCRITO; (3) **o handoff diz PÓS** —
> título `🔁 PÓS-ACIONAMENTO · <serviço>`, de quem se espera, o que falta, o que fazer, e `human_handoff_reason` gravado de verdade;
> (4) **a régua da meta do Founder (≥ 95 %) é medida em TURNOS DE INTENÇÃO sobre o acervo real**, não em mensagens — 📊 56 % das mensagens
> são fragmentos de ≤ 24 caracteres e 88 são "obrigado": contar mensagem passaria de 95 % sem resolver nada (CLAUDE.md §9.5).
>
> **v1.1 · 05/09/2026 · protocolo v11.2 + opção B · marcha PADRÃO (compactada: 1 desenhista, 1 builder, painel de 2 lentes + juiz fresco)** · v1.0 + aquecimento (Opus, 160 mil tokens:
> **nota 78 → 19 emendas E1–E19 aplicadas**, 12 obrigatórias; as duas falsas plantadas — 85 msgs e `vence_em` no helper — achadas por comando, mais duas herdadas: `source_document_id` NULL é 70,3 %, não 100 %, e a ingestão `documents → knowledge_cards` NÃO existe) ·
> nasce da direção direta do Founder em 05/09 (memória `founder-atendimento-directives-097`) + o relatório do investigador (Opus, 146 mil tokens,
> `reality-report-0971.md`, só SELECT, zero PII). Branch `feat/spec097-casa` (continua a 097) · base `origin/main` = `7f3f3eb`.
>
> ⛔ **Travas herdadas da 097 e em vigor:** nenhuma mensagem sai para segurado/seguradora · nenhum agente de atendimento é ligado · InfoCap só leitura ·
> banco SELECT livre, escrita só pelos escritores existentes ou migration da SPEC · nunca imprimir CPF/telefone/apólice/placa/nome/credencial ·
> nada em `.env` de produção · os celulares das atendentes (DDD 48) são reais: **servem para LER conversas, nunca para testar nem para ligar atendimento**.

---

## 0. O TESTE DO PRODUTO

> **Quinta, 15:10. Uma segurada da linha de sinistro pergunta pela terceira vez "e a previsão do vidro?". O agente (quando estiver ligado) NÃO diz
> "vou verificar": diz que a previsão é da seguradora, que o caso está *esperando a loja desde 29/08 (7 dias)* — porque isso está ESCRITO em
> `work_waits` — e que a corretora está cobrando. A oficina parceira manda "aquele caso do para-brisa teve retorno?": o mesmo estado responde,
> porque o caso se explica para quem perguntar. Quando o cliente escreve "o prestador não veio e estou na pista", o agente passa para humano e a
> atendente recebe `🔁 PÓS-ACIONAMENTO · GUINCHO — Quem fala: o segurado · O que ele quer: prestador não chegou · Onde parou: esperando o prestador
> há 1h40 · O que fazer: cobrar a seguradora AGORA e responder aqui`. Nunca "conclua o acionamento".**
>
> E a régua: 📊 sobre os 542 turnos reais do acervo (36 conversas com acionamento), a FUNÇÃO real do motor (E9) rotula cada **turno de intenção** e
> diz o que o produto faria: responde com carta (regra), responde com estado escrito, ou passa para humano com o dossiê PÓS — medido por script,
> com linha de CONTROLE (a mesma passada com o mapa de cartas vazio prevê ≈ só a fatia de regra; o ~40 % do investigador é o teto SEM a U1).
> 🔴 **A meta de ≥ 95 % do Founder é aritmeticamente inalcançável pela própria taxonomia** (📊 283 turnos-mensagem com intenção; 27 são
> não-automatizáveis por desenho — prestador não chegou, reclamação, cancelar, cobrar terceiro, indenização, nova abertura: teto 94,7 % com J,
> 90,5 % sem J). A régua publica o número e o teto; a meta desta SPEC é: **todo turno automatizável por desenho é resolvido (≥ 90 % do total) e
> 100 % do restante chega ao humano com o dossiê PÓS**. A revisão do 95 % está na caixa do Founder (§7).

---

## 1. O QUE FOI MEDIDO (📊 05/09/2026, `reality-report-0971.md`)

| fato | número | consequência |
|---|---|---|
| O corpus do pedido (Resulta · DDD 48) é uma linha ADMINISTRATIVA | 84 conversas: cobrança 60 · apólice 50 · cancelamento 22 · **acionamento reconhecível em 4** | 🔴 a linha de sinistro/assistência, onde o acionamento acontece, está no tenant **AutoFleet** (448 conversas, 448 telefones distintos, DDDs do país inteiro, 100 % espelho do Atlas — real, não simulação; a outra atendente aparece em 78 delas). Corpus adotado: 531 conversas / 21.260 mensagens (AutoFleet inteiro + Resulta DDD 48) → **36 com acionamento**, 1.088 mensagens do cliente depois dele |
| `role='assistant'` nesse acervo é a ATENDENTE HUMANA | 100 % `payload.origem='espelho'`, `sender_user_id` NULL | não há uma mensagem de IA no pós-acionamento: a 097.1 é construção, não correção |
| A mensagem não é a unidade | 56,3 % ≤ 24 caracteres · 18,5 % com `?` · **542 turnos a 2,01 msgs** | R1: o classificador lê o TURNO (rajada sem resposta no meio) |
| 62 % do tráfego pós-acionamento não é do segurado | parceiro/oficina 673 msgs · segurado 254 · indefinido 161 | R2: o estado responde a quem perguntar; o agente não presume que fala com o segurado |
| Taxonomia por intenção (📊 283 msgs com intenção: a taxonomia soma 1.088 exatos, menos 88 social, 84 mídia e 633 fragmentos) | documentos 33 % · agenda 11 % · valores 7 % · oficina 7 % · peça 4 % · carro reserva 2 % · status 3 % · prestador não chegou 3 msgs | 64 % é LOGÍSTICA de reparo, não emergência; regra (D/E/F/C) = 7,5 % do volume; estado (A/B/H/G/J) = 17 % |
| O humano já é excelente | mediana 0,8 min · p90 57,5 min · 1,8 % dos turnos sem resposta | R7: é o PISO; nada da 097.1 pode piorar |
| O caso dura | 6,9 dias · 4,2 episódios · 58 msgs (medianas) · 70× a conversa comum | o caso não cabe numa sessão: o estado tem de ser ESCRITO |
| Hoje no produto | Follow-up não instalado (0/2), `trigger_type='manual'`, sem gatilho; `FOLLOWUP_SYSTEM_PROMPT` é constante de código (`auxiliaries.py:502`), `default_config` nunca é lido pelo draft, `dry_run` hardcoded `True` (l.689), o draft não lê `work_waits` · 📊 `work_steps` `dispatch_phase` = 12 em todo o banco e `captured` NUNCA aparece (os 4 acionamentos são de 18–19/08, antes da migration de `work_waits` de 26/08: a tabela está vazia por falta de TRÁFEGO, não de escritor) · `routines` = 1 linha inativa · 📊 4 agentes `agent_role='attendance'`, `is_active=false`, prompts só de abertura · `work_waits` 0 linhas · `human_handoff_reason` NULL 725/729 · `_TITULOS` sem PÓS · "conclua o acionamento" no ramo de `_o_que_falta` (l.296) | U1–U3 |
| RAG | `knowledge_cards` 18.715 (GLOBAL por desenho — coleção `autobrokers_global`; `source_document_id` NULL em 13.154 = 70,3 %) · `documents`: Resulta 10, **AutoFleet 0** · 🔴 **não existe trilho `documents → knowledge_cards`** (📊 `grep -c knowledge_cards ingestion_service.py` = 0): são dois trilhos, `documents → ingestion_service → Qdrant company_<tenant>` e `conversas → attendance_distiller → knowledge_cards` | as cartas entram por UM trilho declarado (U3.1); a procedência das 13 mil vai para pendência |
| Markdown no WhatsApp | 222 msgs em 60 conversas com `**`, 47 com `##` | fora do escopo → P-097.1-MARKDOWN-NO-CANAL (R11 da 097 no canal) |

---

## 2. REGRAS

- **R1 · A unidade é o TURNO.** O classificador do pós-acionamento recebe a rajada de mensagens do cliente sem resposta entre elas (janela medida no acervo), nunca uma mensagem solta. 📊 542 ≠ 1.088.
- **R2 · O estado responde a quem perguntar.** Segurado, corretor parceiro ou oficina recebem a mesma verdade escrita (`esperando_seguradora` desde …, dito em texto humano como "esperando a loja/seguradora"; `esperando_oficina` NÃO é um `kind`). O agente não presume interlocutor; identifica-o pelo que está na conversa, e na dúvida responde sem nomear papel.
- **R3 · Só se afirma o que está ESCRITO.** Previsão, protocolo, valor, autorização e "já está quase" vêm de `work_waits`/`attendance_sessions`/ficha — nunca do modelo. Sem estado novo, a resposta honesta é "não houve novidade; a corretora está cobrando" (carta C3). Nunca prometer prazo que a seguradora não deu.
- **R4 · A espera é escrita por quem sabe dela.** O corredor abre `work_waits` `kind='esperando_seguradora'`, **`scope='pos_acionamento'`** (distinto de `'acionamento'`, cujo ramo `else` do helper satisfaz toda fase ≠ `needs_human` — E4; o UNIQUE `uq_work_waits_ativo_por_escopo` permite uma ativa por escopo) quando o acionamento entrega protocolo/previsão em **`captured` ou `monitoring`** — ⛔ nunca em `encaminhado`, que já está em `MOTIVO_DO_ESTADO` e ENCERRA o atendimento antes (E5) —, com `vence_em` = previsão informada ou o prazo configurado da corretora; abre `esperando_cliente` (mesmo escopo) quando pede documento; e SATISFAZ a espera quando o estado muda ou quando `marcar_fim` grava o desfecho. Nova espera no mesmo escopo satisfaz a anterior com `satisfeito_por='substituida'`. **Um escritor por estado, no funil existente (`registrar_checkpoint`, chamado de um só lugar); nenhum motor novo (§5).** Nada de dedução por silêncio.
- **R5 · O handoff diz PÓS.** Caso já acionado que vai para humano recebe título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>`, `Quem fala`, `O que ele quer`, `Onde parou` (de quem se espera, desde quando), `Falta`, `O que fazer`. **Proibido** "conclua o acionamento" em caso acionado. E `human_handoff_reason` é GRAVADO (o escritor existe e nunca rodou).
- **R6 · Linguagem de corretora (R11 da 097).** As cartas e o dossiê não têm chave, variável, nome de campo, nem linguagem de apólice; terminam numa próxima ação com dono.
- **R7 · Piso humano.** Nenhum guarda da 097.1 passa se a cadência humana medida (mediana 0,8 min, 1,8 % sem resposta) puder piorar por efeito da SPEC: o agente NÃO responde por cima de conversa assumida (`pausar_ia`, 097) e o Follow-up NÃO envia sozinho (`requires_human_approval=true`, `dry_run=true`).
- **R8 · A meta é medida em turnos de intenção.** A régua exclui social (M), mídia sem texto (Z) e fragmentos sem intenção (N); conta resolvido = respondido com carta ou com estado escrito; não resolvido = foi para humano. Linha de controle: a mesma régua sem as cartas.

---

## 3. UNIDADES

### U1 · O estado existe (R4)
- **U1.1** `dispatch_router.registrar_checkpoint` (📊 um funil, chamado só de `save_active_dispatch:306`): ao gravar `captured`/`monitoring` com protocolo ou previsão, abre `work_waits(kind='esperando_seguradora', scope='pos_acionamento', vence_em, conversation_id, work_run_id)` pelo helper existente **GENERALIZADO** para receber `kind`/`scope`/`vence_em_iso` — hoje `_abrir_espera_do_travamento(db, company_id, session, fase)` só conhece `needs_human` e calcula o prazo de `HANDOFF_ALERTA_MINUTOS`; quem aceita prazo é `abrir_espera(vence_em_iso=)` em `o_fim_do_atendimento.py` (E3). Ao pedir documento ao cliente (`slot` de documento), `esperando_cliente`. 📊 Sem tráfego histórico (`captured` nunca aconteceu): o canário é a única prova viva (E10).
- **U1.2** satisfação: novo estado do corredor, mensagem do cliente com documento (para `esperando_cliente`), ou `marcar_fim` → `status='satisfeito'`, `satisfeito_por`, `satisfeito_em`. `pausar_ia`/claim não mexem na espera.
- **U1.3** `projetarCasos` (097) já lê `work_waits`: a Fila e o Caso passam a mostrar "esperando a seguradora · Nd" com `fonte_id` real. Com DUAS esperas ativas (escopos diferentes), a projeção escolhe a de menor `vence_em`; empate → `pos_acionamento` (E6: hoje o `Map` de `casos.ts` escolhe ao acaso). Sem outra mudança de tela.

### U2 · O handoff diz PÓS (R5)
- **U2.1** `human_handoff.py`: título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>` quando o caso tem acionamento (dispatch_state ∈ captured/monitoring/encaminhado ou `work_waits` ativa); `_o_que_fazer` específico (cobrar a seguradora/loja; pedir documento; reagendar); `Onde parou` lê a espera; `Quem fala` lê a heurística de interlocutor (R2) com "indefinido" honesto.
- **U2.2** `human_handoff_reason` gravado no ponto de handoff. 📊 O escritor existe (`human_handoff.py:608-610`) e só grava com `motivo` não-vazio; nunca rodou porque a tool não corria por `_arun` até 18/08 e os 4 agentes estão desligados — código sem tráfego. A U2.2 define o motivo DEFAULT (`pos_acionamento:<categoria>`) para que nunca vá vazio (E19), e os outros dois caminhos que marcam `HUMAN_REQUESTED` sem motivo (`webhook.py` "Admin Intervention", `espelho_chat.py`) passam a gravar o seu.

### U3 · O agente responde com regra e com estado (R3, R6)
- **U3.1** as seis cartas C1–C6 (`reality-report-0971.md` §3.1) moram em CÓDIGO como dados (`backend/app/atendimento/pos_acionamento.py`: `CARTAS`, `classificar_turno()`, `mapa_de_cartas()`) — decisão nota 88: sem dependência de Qdrant, iguais nos dois tenants, testáveis, e é delas que o bloco do prompt é GERADO (E9; precedente `conhecimento_de_assistencia`). O trilho para o RAG por corretora é `documents → ingestion_service → Qdrant company_<tenant>` (E7): a SPEC entrega `backend/scripts/publicar_cartas_0971.py` que cria os 6 documentos nos dois tenants por esse trilho; ele roda onde há Qdrant (o backend implantado) → caixa do Founder. ⛔ Nenhum trilho novo; nada em `knowledge_cards` (global).
- **U3.2** seção "PÓS-ACIONAMENTO" anexada ao prompt base em `graph.py` (~l.1092), com o MESMO gate `agent_role=='attendance'` do bloco de acionamento; texto gerado de `mapa_de_cartas()` + as regras R2/R3 + "quando não há estado, diga que não há e que a corretora cobra". 📊 4 agentes `attendance` recebem. Sem alterar o fluxo de ABERTURA (regressão zero no corredor: hash do trecho anterior).
- **U3.3** Follow-up `follow-up-whatsapp`: as instruções (a), (b), (c) do §3.2 do relatório entram em `FOLLOWUP_SYSTEM_PROMPT` (`auxiliaries.py:502`, o único prompt que o draft lê — E12) e o payload do draft passa a carregar a ESPERA ativa da conversa (lida de `work_waits` pelo caminho da 097) — sem ela, "onde o caso está" e "de quem se espera" são impossíveis de obedecer. `dry_run` continua `True` (hardcoded, l.689) e o endpoint continua manual. `default_config` guarda só o contrato (data migration idempotente, sem ser lido pelo draft). 🔴 O GATILHO de silêncio (X horas sem mensagem da corretora) fica FORA: não existe motor de Rotina rodando (📊 `routines` 1 linha inativa, `last_run_at` NULL 4/4) e criá-lo aqui seria motor paralelo → **P-097.1-GATILHO-DO-FOLLOW-UP**.

### U4 · A régua da meta (R8)
- **U4.1** `backend/scripts/regua_0971.py` (só SELECT, zero PII na saída, sem LLM): reconstrói os TURNOS do acervo (regra §0.4 do relatório, MESMO motor), rotula cada turno com `classificar_turno()` REAL (rótulo = primeira categoria ≠ M/N/Z da rajada; denominador = turnos com rótulo ∉ {M,N,Z}), e imprime em linhas separadas: `resolvido_por_carta` (rótulo com carta em `mapa_de_cartas()`: D,E,F,C,B,H) · `estado_REAL` (rótulo ∈ {A,G,J} com `work_waits` ativa no instante do turno — 📊 hoje 0, e a régua DIZ isso) · `estado_SIMULADO` (os mesmos rótulos, se a U1 tivesse escrito — 💭) · `para_humano` (I,K1,K2,K3,L e A/G/J sem espera) · **% resolvido REAL e % SIMULADO** · o TETO de desenho · a linha de CONTROLE (`mapa_de_cartas()` vazio). Publica o próprio denominador.
- **U4.2** o número vai ao relatório com 📊, ao lado do teto (94,7 %/90,5 %); a SPEC não mente: diz o número e o que falta (§6).

### E · Canário (Amandus → Resulta → AutoFleet, sem mensagem)
`backend/scripts/canario_0971.py --vivo` (`AUTOBROKERS_CANARIO=1`): episódio canário na Resulta → o corredor dublê grava `captured` com previsão → `work_waits` ativa com `vence_em` e corretora → a projeção da 097 mostra "esperando a seguradora" com `fonte_id` (CONTROLE: antes da escrita, `esperando: null`) → handoff dublê gera o dossiê com `🔁 PÓS-ACIONAMENTO` e `human_handoff_reason` gravado (CONTROLE: caso sem acionamento gera o título antigo) → `marcar_fim` satisfaz a espera → limpeza 0/0/0 por id e corretora.

### G · Guardas (desenhista escreve antes; gate zero VERMELHO em cópia limpa)
- `backend/tests/test_o_caso_se_explica_sozinho.py`: [A] o corredor abre a espera ao capturar (motor real, dublê de banco) e NÃO abre sem protocolo/previsão (controle) · [B] `marcar_fim` satisfaz a espera · [C] o dossiê de um caso acionado tem o título PÓS, `Onde parou` e nunca "conclua o acionamento" (um caso histórico anonimizado: o dossiê antigo fica VERMELHO) · [D] `human_handoff_reason` é gravado · [E] o prompt base tem a seção e o fluxo de abertura é IDÊNTICO (hash do trecho) · [F] as 6 cartas passam pelo guarda de linguagem humana da 097 (`[13]`: sem chave, sem `@N`, sem snake_case) · [G] a régua reproduz ≥ 3 números do §1 e a linha de controle sem cartas dá menos que com cartas · [H] Follow-up: chama o `POST /follow-up-whatsapp/draft` REAL (dublê de banco, com a Espera no payload) e prova `dry_run: true` NA RESPOSTA e zero chamada de envio; mutação `auxiliaries.py:689` → `False` fica VERMELHO (E11) · [J] `classificar_turno()`/`mapa_de_cartas()` geram o bloco do prompt: mudar o mapa muda o prompt (E9) · [K] escopo: abrir em `acionamento` e em `pos_acionamento` dá DUAS ativas; `encaminhado` NÃO abre (E4/E5) · [L] duas esperas ativas → a projeção escolhe a de menor `vence_em` (E6) · [I] nada de motor novo (`grep` por scheduler/cron/listener novos = zero).
- `--mutar`: escrita da espera removida · título PÓS removido · "conclua o acionamento" de volta · `dry_run=false` — cada uma VERMELHA por NOME.

---

## 4. ORDEM E GATES
```
desenhista (guardas, gate zero vermelho) → builder backend (U1, U2, U3.2, U3.3, U4, E) → cartas C1–C6 ingeridas nos 2 tenants (U3.1, pelo caminho existente)
→ red team ‖ lente DADO+verdade (uma lente, dois olhos) → consertos → juiz fresco + canário vivo → suíte inteira (árvore parada) → relatório → push
```

## 5. O QUE FICOU FORA (com o gatilho)
- gatilho de silêncio do Follow-up (motor de Rotina) → P-097.1-GATILHO-DO-FOLLOW-UP (destrava: a SPEC-058 de Rotinas rodar de verdade)
- ligar os agentes de atendimento → decisão do Founder (WhatsApp religado); a 097.1 deixa PRONTO e desligado
- classificar mídia (áudio/foto/PDF, 📊 84 msgs) → P-097.1-MIDIA-SEM-TEXTO
- markdown no WhatsApp (📊 222 msgs) → P-097.1-MARKDOWN-NO-CANAL
- procedência das 18.715 cartas (`source_document_id` NULL) → P-097.1-CARTAS-SEM-PROCEDENCIA (SPEC-052)
- a linha da atendente mistura caso, colegas e vida pessoal → decisão do Founder ANTES de ligar IA num número real → caixa

## 6. PENDÊNCIAS QUE ESTA SPEC ABRE
P-097.1-GATILHO-DO-FOLLOW-UP · P-097.1-MIDIA-SEM-TEXTO · P-097.1-MARKDOWN-NO-CANAL · P-097.1-CARTAS-SEM-PROCEDENCIA (📊 13.154/18.715) · P-097.1-CARTAS-NO-RAG (rodar o publicador no implantado) · P-097.1-RAG-AUTOFLEET-VAZIO (📊 0 documentos onde o pós-acionamento acontece; as 6 cartas são o primeiro) · P-097.1-LINHA-COMPARTILHADA (decisão).

## 7. A CAIXA DO FOUNDER
0. 🔴 **A meta de 95 % não fecha na aritmética do acervo** (teto 94,7 % com J / 90,5 % sem J; 27 turnos são humanos por desenho). Decida: (a) a meta vira "todo automatizável resolvido + 100 % do resto com dossiê PÓS" (o que a SPEC faz), (b) J e L contam como resolvidos por estado (94,7 %), ou (c) mantém 95 % e aceita que a régua fique vermelha.
1. 🔴 A linha de acionamento vive no tenant **AutoFleet** (espelho do WhatsApp da segunda atendente), não na Resulta/DDD 48: confirme que é isso mesmo — e que as cartas devem nascer nos DOIS tenants (é o que a SPEC faz).
2. Quando religar o WhatsApp: os agentes seguem `is_active=false` até você ligar; o Follow-up segue `dry_run=true` (rascunho, aprovação humana).
3. Decidir sobre a linha compartilhada (caso + colegas + pessoal no mesmo número) antes de ligar IA num número de atendente real.
4. O gatilho automático do Follow-up depende de Rotinas rodarem (SPEC-058) — hoje nenhuma roda.
5. Depois do deploy: rodar `python scripts/publicar_cartas_0971.py --vivo` no backend implantado (onde há Qdrant) para as 6 cartas entrarem no RAG dos dois tenants (P-097.1-CARTAS-NO-RAG).
