# SPEC-097.1 · O CASO SE EXPLICA SOZINHO — o pós-acionamento é uma FASE do atendimento: tem estado, o agente responde com ele, acompanha sozinho, e o que sobra vai para humano dizendo que é PÓS

> **O que ela entrega:** depois que o acionamento é feito (protocolo, prestador, previsão), o atendimento **continua** — e hoje o produto tem **zero** nesse trecho:
> 📊 os 4 agentes de atendimento estão `is_active=false` e os prompts (1,5 KB) só cobrem a ABERTURA; o Auxiliar `follow-up-whatsapp` não está instalado em nenhum
> tenant e é um gerador de rascunho manual; `work_waits` tem 0 linhas (por falta de tráfego: nenhum `captured` desde a migration de 26/08); `human_handoff_reason` é
> NULL em 725/729; o dossiê de handoff não tem título de pós-acionamento e diz *"conclua o acionamento"* para um caso já acionado.
> A 097.1 **preenche** o que a 097 construiu (`Caso`/`Agora`/`Espera`/`ProximaAcao`, estágios `protocolo`/`monitorando`/`esperando`/`parado`/`concluido`):
> (1) **o estado existe** — o corredor ESCREVE de quem se espera e desde quando (`work_waits`), no ponto em que o acionamento vira espera;
> (2) **o acompanhamento é uma FASE automática do atendimento** (abertura → acionamento → **acompanhamento**), ligada por padrão, com um desligador por corretora —
> não é Rotina, não é Auxiliar: são três gatilhos que já existem no produto (o cliente escreve; o corredor muda o estado; a espera vence no vigia que já roda a cada 10 min);
> (3) **o agente responde com regra e com estado** — seis cartas em linguagem de corretora e uma seção de pós-acionamento no prompt que só afirma o que está ESCRITO;
> (4) **o handoff diz PÓS** — título `🔁 PÓS-ACIONAMENTO · <serviço>`, de quem se espera, o que falta, o que fazer, `human_handoff_reason` gravado — e **o handoff
> com dossiê completo ENCERRA a parte do agente** (🧑 decisão do Founder, 05/09): o caso fica aberto para a corretora, mas para o AutoBrokers aquele turno está resolvido;
> (5) **duas réguas, medidas em TURNOS DE INTENÇÃO sobre o acervo real**: *resolvido pelo agente* (carta, estado ou handoff PÓS) e, ao lado, *resolvido sem humano* —
> para que o número do Founder (≥ 95 %) seja verdadeiro e o esforço humano continue visível; (6) **só atendimento vira conhecimento**: conversa pessoal ou entre colegas
> na linha da atendente é descartada antes de virar carta ou régua (🧑 05/09).
>
> **v1.2 · 05/09/2026 · protocolo v11.2 + opção B · marcha PADRÃO (compactada: 1 desenhista, 1 builder, painel de 2 lentes + juiz fresco)** · v1.1 (aquecimento Opus
> 160 mil tokens: **nota 78 → 19 emendas E1–E19**; as duas falsas plantadas — 85 msgs e `vence_em` no helper — achadas por comando, mais duas herdadas:
> `source_document_id` NULL é 70,3 %, não 100 %, e a ingestão `documents → knowledge_cards` NÃO existe) + **a direção do Founder de 05/09 à noite** (memória
> `founder-pos-acionamento-directives-0971`): handoff = a parte do agente terminou; acompanhamento é fase, não Rotina; pessoal descartado; AutoFleet = Regina, Resulta =
> Saionara; publicador passo a passo. Branch `feat/spec097-casa` (continua a 097, já na `main` em `d758b81`) · base `origin/main` = `7f3f3eb`.
>
> ⛔ **Travas herdadas da 097 e em vigor:** nenhuma mensagem sai para segurado/seguradora · nenhum agente de atendimento é ligado (`agents.is_active` não muda) · InfoCap
> só leitura · banco SELECT livre, escrita só pelos escritores existentes ou migration da SPEC · nunca imprimir CPF/telefone/apólice/placa/nome/credencial · nada em `.env`
> de produção · os celulares das atendentes são reais: **servem para LER conversas, nunca para testar nem para ligar atendimento**; o número pode mudar — nada se ancora nele.

---

## 0. O TESTE DO PRODUTO

> **Quinta, 15:10. Uma segurada da linha de sinistro pergunta pela terceira vez "e a previsão do vidro?". O agente NÃO diz "vou verificar": diz que a previsão é da
> seguradora, que o caso está *esperando a loja desde 29/08 (7 dias)* — porque isso está ESCRITO em `work_waits` — e que a corretora está cobrando. Às 16:00 a loja
> devolve a previsão pelo corredor: o estado muda e **o agente avisa a segurada sem ninguém pedir** (acompanhamento). Se a loja não responder até o prazo, o vigia que
> já roda a cada 10 minutos vence a espera: a equipe é avisada (como hoje) **e** a segurada recebe "ainda sem novidade; estamos cobrando" — nunca uma previsão inventada.
> A oficina parceira manda "aquele caso do para-brisa teve retorno?": o mesmo estado responde. Quando a segurada escreve "o prestador não veio e estou na pista",
> o agente passa para humano com `🔁 PÓS-ACIONAMENTO · GUINCHO — Quem fala: a segurada · O que ela quer: prestador não chegou · Onde parou: esperando o prestador há 1h40
> · O que fazer: cobrar a seguradora AGORA e responder aqui` — e **a parte do agente acabou**: o turno conta como resolvido pelo AutoBrokers; o caso segue aberto na
> Fila da corretora até alguém encerrar. Nunca "conclua o acionamento".**
>
> E a régua: 📊 sobre os 542 turnos reais do acervo (36 conversas com acionamento, 283 mensagens com intenção), a FUNÇÃO real do motor rotula cada turno e diz o que o
> produto faria: carta, estado, ou handoff PÓS. **`resolvido_pelo_agente` ≥ 95 %** (carta + estado + handoff com dossiê completo; o que sobra é turno sem intenção
> reconhecível) e, na linha de baixo, **`resolvido_sem_humano`** (só carta + estado — 📊 teto de desenho 90,5 %/94,7 %) — os dois publicados, com linha de CONTROLE
> (mapa de cartas vazio) e com o denominador.

---

## BLOCO 0 · Remedir antes de codar (o censo que vira régua)

Antes do primeiro builder, o guarda [G] reproduz sobre o acervo (só SELECT, zero PII) os 📊 desta §1 — 36 conversas com acionamento · 1.088 mensagens do cliente depois
do `t0` · 542 turnos · 283 com intenção · 27 humanos por desenho — com a regra §0.4 do `reality-report-0971.md` no MESMO motor (Postgres com `translate` de acentos,
CLAUDE.md §9.4). Um número que não reproduz é emenda, não é build. O gate zero do desenhista já ficou VERMELHO em cópia limpa (📊 18 ok · 20 falhas, `8529008`).

## 1. O QUE FOI MEDIDO (📊 05/09/2026, `reality-report-0971.md` + aquecimento)

| fato | número | consequência |
|---|---|---|
| A linha da Resulta (Saionara) é ADMINISTRATIVA; a de acionamento é a da AutoFleet (Regina) | Resulta/48: 84 conversas — cobrança 60 · apólice 50 · cancelamento 22 · **acionamento reconhecível em 4**. AutoFleet: 448 conversas, 448 telefones distintos, DDDs do país inteiro, protocolo em 52, vidro 44, guincho 26 | corpus = as duas linhas (531 conversas / 21.260 mensagens) → **36 com acionamento**, 1.088 mensagens do cliente depois dele. 🧑 Confirmado pelo Founder: AutoFleet = Regina, Resulta = Saionara |
| `role='assistant'` nesse acervo é a ATENDENTE HUMANA | 100 % `payload.origem='espelho'`, `sender_user_id` NULL | não há uma mensagem de IA no pós-acionamento: a 097.1 é construção |
| A mensagem não é a unidade | 56,3 % ≤ 24 caracteres · 18,5 % com `?` · **542 turnos a 2,01 msgs** | R1: o classificador lê o TURNO |
| 62 % do tráfego pós-acionamento não é do segurado | parceiro/oficina 673 msgs · segurado 254 · indefinido 161 | R2: o estado responde a quem perguntar |
| Taxonomia por intenção (📊 283 msgs: a taxonomia soma 1.088, menos 88 social, 84 mídia, 633 fragmentos) | documentos 124 · agenda 42 · valores 27 · oficina 25 · peça 14 · cobrar terceiro 12 · status 11 · carro reserva 9 · indenização 6 · cobertura 4 · prestador não chegou 3 · nova abertura 3 · reclamação 2 · cancelar 1 | 64 % é LOGÍSTICA de reparo; 27 turnos-mensagem são humanos por desenho (§2 R9) |
| A linha mistura caso, colegas e vida pessoal | 633 mensagens "N": fragmentos, coordenação entre colegas, papo pessoal | R11: filtro de atendimento antes de carta ou régua (🧑 "tudo que for pessoal deve ser descartado") |
| O humano já é excelente | mediana 0,8 min · p90 57,5 min · 1,8 % dos turnos sem resposta | R7: é o PISO |
| O caso dura | 6,9 dias · 4,2 episódios · 58 msgs (medianas) · 70× a conversa comum | o estado tem de ser ESCRITO |
| Hoje no produto | Follow-up não instalado (0/2), manual, `FOLLOWUP_SYSTEM_PROMPT` constante de código (`auxiliaries.py:502`), `dry_run` hardcoded (l.689), não lê `work_waits` · `routines` 1 linha inativa · 4 agentes `attendance` `is_active=false`, prompts só de abertura · `work_waits` 0 linhas (📊 `dispatch_phase` = 12 em todo o banco, `captured` nunca) · `human_handoff_reason` NULL 725/729 · `_TITULOS` sem PÓS · "conclua o acionamento" no ramo de `_o_que_falta` (l.296) | U1–U4 |
| 🔴 O vigia das esperas JÁ RODA em produção | `buffer_processor.py:506` agenda `varrer_esperas_vencidas` (APScheduler, a cada 10 min, `HANDOFF_WATCHDOG_INTERVAL_MINUTES`): avisa a equipe pelo canal existente, conta `avisos`, expira em `AVISOS_ATE_EXPIRAR` | R10: o acompanhamento não precisa de Rotina nem de motor novo — engata no vigia (§5) |
| Um funil só para o corredor | `registrar_checkpoint` (`dispatch_router.py:1081`) é chamado de um lugar (`save_active_dispatch:306`); o helper `_abrir_espera_do_travamento(db, company_id, session, fase)` só conhece `needs_human`; `encaminhado` ∈ `MOTIVO_DO_ESTADO` e ENCERRA | U1.1 toca 1 ponto; espera só em `captured`/`monitoring` |
| RAG | `knowledge_cards` 18.715 (GLOBAL, coleção `autobrokers_global`; `source_document_id` NULL em 13.154 = 70,3 %) · `documents`: Resulta 10, AutoFleet 0 · não existe trilho `documents → knowledge_cards` | cartas em código + publicador pelo trilho `documents → ingestion_service → Qdrant company_<tenant>` |
| Toggle por corretora | `companies.acionamento_profile` (jsonb) existe; `companies.agent_enabled` existe | o desligador do acompanhamento mora em `acionamento_profile.acompanhamento` (padrão ligado) |
| Markdown no WhatsApp | 222 msgs em 60 conversas com `**`, 47 com `##` | fora → P-097.1-MARKDOWN-NO-CANAL |

---

## 2. REGRAS

- **R1 · A unidade é o TURNO.** A rajada de mensagens do cliente sem resposta entre elas, nunca uma mensagem solta. 📊 542 ≠ 1.088.
- **R2 · O estado responde a quem perguntar.** Segurado, parceiro ou oficina recebem a mesma verdade escrita (`esperando_seguradora` desde …, dito em texto humano;
  `esperando_oficina` NÃO é um `kind`). O agente não presume interlocutor; na dúvida responde sem nomear papel.
- **R3 · Só se afirma o que está ESCRITO.** Previsão, protocolo, valor, autorização e "já está quase" vêm de `work_waits`/`attendance_sessions`/ficha — nunca do modelo.
  Sem estado novo, a resposta honesta é "não houve novidade; a corretora está cobrando". Nunca prometer prazo que a seguradora não deu.
- **R4 · A espera é escrita por quem sabe dela.** `registrar_checkpoint` abre `work_waits` `kind='esperando_seguradora'`, **`scope='pos_acionamento'`** (distinto de
  `'acionamento'`; o UNIQUE `uq_work_waits_ativo_por_escopo` permite uma ativa por escopo) em **`captured` ou `monitoring`** com protocolo/previsão — ⛔ nunca em
  `encaminhado` —, `vence_em` = previsão informada ou o prazo configurado; abre `esperando_cliente` quando pede documento; SATISFAZ quando o estado muda ou `marcar_fim`
  grava o desfecho; nova espera no mesmo escopo satisfaz a anterior com `satisfeito_por='substituida'` (📊 hoje a segunda seria PERDIDA no UNIQUE — achado do gate zero
  [B3p]/[K2]). **Um escritor por estado, no funil existente; nenhum motor novo (§5).** Nada de dedução por silêncio.
- **R5 · O handoff diz PÓS.** Caso já acionado que vai para humano recebe título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>`, `Quem fala`, `O que ele quer`, `Onde parou` (de quem se
  espera, desde quando), `Falta`, `O que fazer`. **Proibido** "conclua o acionamento" em caso acionado. `human_handoff_reason` é GRAVADO com default `pos_acionamento:<rótulo>`.
- **R6 · Linguagem de corretora (R11 da 097).** Cartas e dossiê sem chave, variável, nome de campo ou linguagem de apólice; terminam numa próxima ação com dono.
- **R7 · Piso humano.** Nada da 097.1 piora a cadência humana (mediana 0,8 min, 1,8 % sem resposta): o agente NÃO responde por cima de conversa assumida (`pausar_ia`),
  e nada sai enquanto o agente da corretora estiver desligado (`agents.is_active`, `companies.agent_enabled`) — a 097.1 deixa PRONTO e desligado.
- **R8 · Duas réguas, uma unidade.** Sobre turnos de intenção (rótulo ∉ {M,N,Z}): `resolvido_pelo_agente` = carta ∨ estado ∨ **handoff com dossiê PÓS completo**
  (🧑 "entregar para o humano é um status em que o agente não tem mais o que fazer"); `resolvido_sem_humano` = carta ∨ estado. Os dois publicados, com o teto de desenho e a
  linha de CONTROLE (mapa vazio). ⛔ Um handoff SEM `Onde parou` e `O que fazer` não conta — senão "handoff" vira carimbo (CLAUDE.md §9.5).
- **R9 · O que vai para humano por desenho — e conta como resolvido pelo agente quando o dossiê está completo:**
  ```
  K1  prestador não chegou / cliente em local de risco       → humano AGORA (segurança antes do atendimento); o agente já cobra a seguradora no dossiê
  K2  reclamação, insatisfação, "é mentira", tom de conflito → humano (relacionamento não se automatiza)
  K3  cancelar / desistir do serviço                          → humano (é decisão com consequência na apólice)
  J   pedir que a corretora cobre a seguradora/oficina        → humano executa a cobrança; o agente registra o pedido no estado e responde que está cobrando
  L   indenização / pagamento / prazo de pagamento            → humano (valor e data só a seguradora dá; o agente diz isso e passa)
  F*  cobertura ou direito que NÃO está numa carta            → humano (cobertura é contrato; a InfoCap é só leitura)
  B*  documento ilegível/incompleto depois de 2 pedidos       → humano (a carta C5 cobre o 1º e o 2º pedido)
  E*  negociação de franquia/valor (não é "como funciona")    → humano
  Z   mídia sem texto que o agente não entende                → humano com a mídia anexada ao dossiê
  I   nova abertura no mesmo fio                              → NÃO é handoff: volta ao corredor de acionamento (novo episódio)
  P   cliente pede uma pessoa, ameaça, urgência médica, vítimas, acidente em curso → humano AGORA
  ```
  Tudo o mais (A status, B documentos, C agenda/vistoria, D carro reserva, E franquia como regra, F cobertura que está em carta, G oficina/credenciada, H peça/previsão) o
  agente resolve com carta ou estado. A lista é DADO do módulo (`SITUACOES_PARA_HUMANO`), lida pelo prompt, pelo handoff e pela régua — uma fonte só.
- **R10 · O acompanhamento é uma FASE do atendimento, automática, ligada por padrão.** Começa em `captured`/`monitoring` e termina no desfecho. Três gatilhos, nenhum
  novo: (a) **o cliente escreve** → o agente de atendimento responde com estado (U3.2); (b) **o corredor muda o estado/previsão** (`registrar_checkpoint`) → o agente
  manda a novidade ao cliente sem ninguém pedir (U5.1); (c) **a espera vence** no vigia que já roda (`varrer_esperas_vencidas`, 10 min) → a equipe é avisada como hoje **e**
  o cliente recebe "ainda sem novidade; a corretora está cobrando" (U5.2), respeitando `avisos`/`AVISOS_ATE_EXPIRAR`. O desligador por corretora é
  `companies.acionamento_profile.acompanhamento = false` (padrão: ligado); R7 continua valendo — nada sai com o agente desligado ou a conversa assumida. O Auxiliar
  `follow-up-whatsapp` NÃO é o motor: continua sendo o rascunho manual para a atendente, agora lendo o estado (U3.3).
- **R11 · Só atendimento vira conhecimento.** Antes de uma conversa da linha da atendente virar carta (`attendance_distiller`) ou entrar na régua, passa por
  `e_atendimento_de_seguro(conversa)` — vocabulário de seguro/assistência/sinistro presente, sem marcadores de coordenação entre colegas ou de vida pessoal. O que não
  passa é DESCARTADO e contado (nunca lido por agente, nunca carta). 🧑 "conversas pessoais não devem ir para o RAG; o número pode mudar".

---

## 3. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3)

| referência | o que faz | o que a 097.1 modela |
|---|---|---|
| Intercom · SLAs em conversas e tickets (https://www.intercom.com/help/en/articles/6546152-set-slas-for-conversations-and-tickets) | o SLA é um relógio ESCRITO no ticket; o bot responde com o estado do ticket, não com promessa | `work_waits.vence_em` é o relógio; o agente só cita o que está na espera (R3) |
| Zendesk · triggers em atualização de ticket (https://support.zendesk.com/hc/en-us/articles/4408886227738-Creating-triggers-for-automatic-ticket-updates-and-notifications) | a mudança de estado DISPARA a mensagem ao cliente; não há cron: é evento | R10(b): o checkpoint do corredor manda a novidade; R10(c): o vencimento da espera é o único "relógio", e ele já existe |
| Front · regras com condição de tempo "sem resposta em X" (https://help.front.com/en/articles/2113) | a regra avisa a equipe e pode responder ao cliente com um texto honesto | `varrer_esperas_vencidas` já avisa a equipe; a 097.1 acrescenta a mensagem honesta ao cliente, com teto de avisos |
| Salesforce · Case timeline / milestones (https://help.salesforce.com/s/articleView?id=service.cases_set_up_and_manage_the_case_timeline.htm&language=en_US&type=5) | o caso tem marcos visíveis a quem perguntar; o humano vê "de quem se espera" | o Caso da 097 mostra a Espera com `fonte_id`; o handoff PÓS lê o mesmo estado (R5) |
| Google · Agent Assist, resumo de handoff (https://cloud.google.com/agent-assist/docs/summarization) | o resumo é estruturado (o que o cliente quer, o que foi feito, o que falta) — e o bot encerra a parte dele ao entregar | R5 + R8: dossiê estruturado; a parte do agente termina no handoff |

### COMO O JUIZ INSPECIONA
Cada linha acima tem um guarda que a EXECUTA: [A]/[B]/[K] a espera; [C]/[D] o dossiê; [E]/[J] o prompt gerado; [G] a régua com as duas linhas; [H] o draft que não envia;
[M] o checkpoint que muda o estado gera a novidade ao cliente (com o agente desligado: gerada e NÃO enviada — registrada como `suprimida`); [N] a espera vencida no vigia gera a
mensagem honesta com teto e respeita o desligador; [O] `e_atendimento_de_seguro` descarta pessoal/colegas (com controle: atendimento real passa).

---

## 4. UNIDADES

### U1 · O estado existe (R4)
- **U1.1** `registrar_checkpoint`: em `captured`/`monitoring` com protocolo ou previsão → `abrir_espera(kind='esperando_seguradora', scope='pos_acionamento', vence_em_iso=
  previsão ou agora+prazo, conversation_id, work_run_id, fonte_id)` pelo helper `_abrir_espera_do_travamento` GENERALIZADO (`kind`/`scope`/`vence_em_iso`; hoje só
  `needs_human`, prazo de `HANDOFF_ALERTA_MINUTOS`); pedido de documento → `esperando_cliente`. Nunca em `encaminhado`. 📊 Sem tráfego histórico: o canário é a prova.
- **U1.2** `marcar_fim` satisfaz as esperas ativas (`satisfeito_por='desfecho'`); abrir no mesmo escopo satisfaz a anterior (`'substituida'`) ANTES de inserir.
- **U1.3** `projetarCasos`: entre esperas ativas, a de menor `vence_em`; empate → `pos_acionamento`. O guarda mjs ganha a conversa com duas esperas e `--fila-json` expõe `work_waits`.

### U2 · O handoff diz PÓS e encerra a parte do agente (R5, R8, R9)
- **U2.1** `human_handoff.py`: título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>` quando acionado; `Quem fala` (segurado/parceiro/indefinido — honesto), `O que ele quer` (rótulo
  humano), `Onde parou` (texto da espera), `Falta`, `O que fazer` por situação de `SITUACOES_PARA_HUMANO`. "conclua o acionamento" NUNCA em caso acionado.
- **U2.2** `human_handoff_reason` default `pos_acionamento:<rótulo>`; `webhook.py` (Admin Intervention) e `espelho_chat.py` gravam o seu motivo.
- **U2.3** o handoff PÓS grava na conversa `ficha_atendimento.agente_concluiu = {em, motivo}` (jsonb existente, sem coluna nova) — o que a régua e a Fila leem como
  "o AutoBrokers terminou a parte dele"; `resolvido_em` continua sendo o desfecho da CORRETORA. O card da Fila/Caso da 097 mostra "entregue à equipe · há 2h".

### U3 · O agente responde com regra e com estado (R3, R6)
- **U3.1** `backend/app/atendimento/pos_acionamento.py`: `CARTAS` C1–C6, `CATEGORIAS`, `SITUACOES_PARA_HUMANO`, `classificar_turno()`, `mapa_de_cartas()`,
  `bloco_do_prompt()` (GERADO), `texto_da_espera()`, `e_atendimento_de_seguro()`. Publicador `backend/scripts/publicar_cartas_0971.py` pelo trilho
  `documents → ingestion_service` nos dois tenants (roda onde há Qdrant — §7 passo a passo).
- **U3.2** `graph.py`: bloco PÓS-ACIONAMENTO anexado com o gate `agent_role=='attendance'`, depois do bloco de acionamento; trecho anterior byte a byte igual (hash no guarda).
- **U3.3** `auxiliaries.py`: `FOLLOWUP_SYSTEM_PROMPT` com as instruções (a)(b)(c); o draft lê a espera ativa e a põe no payload como `estado`; resposta expõe `dry_run: true`;
  sem espera → "não houve novidade" e zero previsão. Migration `20260905_02` (data, idempotente, NÃO aplicada pelo builder): `auxiliary_templates.default_config` ganha o contrato.

### U4 · As duas réguas (R8)
- **U4.1** `backend/scripts/regua_0971.py`: `medir(turnos)` puro + `main()` (SELECT, os dois tenants, `e_atendimento_de_seguro` aplicado e contado); imprime denominador ·
  `resolvido_por_carta` · `estado_REAL` (📊 hoje 0, dito) · `estado_SIMULADO` (💭) · `handoff_pos` (por `SITUACOES_PARA_HUMANO`) · `para_humano_sem_dossie` (o que
  sobra) · **% resolvido_pelo_agente** · **% resolvido_sem_humano** · teto · CONTROLE (mapa vazio) · descartados por R11.
- **U4.2** os números vão ao relatório com 📊; a SPEC não mente.

### U5 · O acompanhamento (R10) — a fase que já tem os gatilhos
- **U5.1** `registrar_checkpoint`: quando o estado/previsão MUDA em `captured`/`monitoring`, gera `novidade_ao_cliente` (texto humano da carta C3 com o estado) e a entrega
  ao caminho de resposta do agente de atendimento da conversa (o mesmo que responde ao cliente hoje; `pausar_ia` respeitado); com o agente desligado ou
  `acionamento_profile.acompanhamento=false`, a novidade é gerada e **suprimida** (registrada com `suprimida_por` no log/`work_events`), nunca enviada.
- **U5.2** `varrer_esperas_vencidas`: para `scope='pos_acionamento'`, além do aviso à equipe (existente), gera a mensagem honesta ao cliente ("ainda sem novidade; a corretora
  está cobrando"), uma por aviso, até `AVISOS_ATE_EXPIRAR`; mesma supressão de U5.1. Nenhum job novo: é um ramo dentro do vigia que já roda.
- **U5.3** o desligador: `companies.acionamento_profile.acompanhamento` (ausente = ligado); lido pelos dois gatilhos.

### E · Canário (Resulta, linhas próprias, `AUTOBROKERS_CANARIO=1`, nada sai)
episódio+conversa canário → checkpoint `captured` com previsão pelo MOTOR real → `work_waits` ativa (CONTROLE antes: nenhuma) → o checkpoint muda a previsão → a novidade
é GERADA e SUPRIMIDA (agente desligado) com `suprimida_por` gravado → o vigia dublado vence a espera → mensagem honesta gerada e suprimida, `avisos`=1 → handoff dublê:
título PÓS, `human_handoff_reason` e `agente_concluiu` gravados (CONTROLE: caso sem acionamento → título antigo) → `marcar_fim` satisfaz → limpeza 0/0/0 por id e corretora.

### G · Guardas (desenhista, antes; gate zero VERMELHO em `8529008`; v1.2 acrescenta [M][N][O][Q])
[A] espera nasce no funil (controles: sem protocolo → 0; `encaminhado` → 0; escopo `acionamento` intocado) · [B] `marcar_fim` satisfaz; substituída · [K] dois escopos →
duas ativas · [C] dossiê PÓS com `Onde parou`/`O que fazer`, nunca "conclua"; dossiê antigo REPROVA · [D] `human_handoff_reason` gravado · [E] prompt gerado, gate attendance,
abertura idêntica (hash) · [J] mudar o mapa muda o prompt · [F] cartas em linguagem humana · [G] a régua com as DUAS linhas e o controle · [H] draft com `dry_run: true` na
resposta, espera no payload, zero envio · [L] duas esperas → menor `vence_em` · [I] nenhum motor novo · **[M]** checkpoint que muda o estado gera a novidade; agente
desligado → suprimida, nunca enviada (dublê de outbound = 0 chamadas) · **[N]** espera vencida no vigia gera a mensagem honesta, respeita `avisos` e o desligador · **[O]**
`e_atendimento_de_seguro` descarta pessoal/colegas e aceita atendimento (controle) · **[Q]** handoff PÓS grava `agente_concluiu` e a régua o conta; handoff SEM `Onde parou`
NÃO conta. Mutações por cópia, subprocesso, nome novo: U1, U1B, U1C, U2, U2B, U2C, U3, U3B, U4, U4B, U5, U5B, **U6** (novidade enviada com agente desligado), **U6B**
(vigia ignora o desligador), **U7** (filtro deixa passar pessoal), **U8** (handoff sem `Onde parou` conta).

---

## 5. O QUE SAIU — e o gatilho que faz voltar (CLAUDE.md §11)
- **Rotina/cron para o acompanhamento** — saiu por decisão do Founder e por §5: os três gatilhos já existem (evento do corredor, mensagem do cliente, vigia de 10 min). Volta: nunca.
- **Follow-up como Auxiliar instalado** — o Auxiliar fica como rascunho manual; não é o motor. Volta se uma corretora quiser follow-up por e-mail/outro canal.
- **Classificar mídia** (📊 84 msgs áudio/foto/PDF) → P-097.1-MIDIA-SEM-TEXTO. Volta com transcrição no canal.
- **Markdown no WhatsApp** (📊 222 msgs) → P-097.1-MARKDOWN-NO-CANAL. Volta como conserto do canal (R11 da 097).
- **Procedência das 13.154 cartas sem `source_document_id`** → P-097.1-CARTAS-SEM-PROCEDENCIA (SPEC-052).
- **Reconhecer o interlocutor por identidade** (parceiro × segurado): fica heurístico e honesto ("indefinido"). Volta com cadastro de parceiros.
- **Ligar os agentes** — nunca por esta SPEC; decisão do Founder ao religar o WhatsApp.

## 6. PENDÊNCIAS QUE ESTA SPEC ABRE
P-097.1-MIDIA-SEM-TEXTO · P-097.1-MARKDOWN-NO-CANAL · P-097.1-CARTAS-SEM-PROCEDENCIA (📊 13.154/18.715) · P-097.1-CARTAS-NO-RAG (rodar o publicador no implantado) ·
P-097.1-RAG-AUTOFLEET-VAZIO (📊 0 documentos) · P-097.1-INTERLOCUTOR-POR-CADASTRO · P-097.1-ACOMPANHAMENTO-NA-CENTRAL (o toggle na tela da Central de Agentes).

## 7. A CAIXA DO FOUNDER
1. **Meta:** decidido por você — handoff com dossiê completo conta como resolvido pelo agente (`resolvido_pelo_agente` ≥ 95 %); o número "sem humano" fica publicado ao lado.
2. **Quando religar o WhatsApp:** os agentes seguem `is_active=false` até você ligar; o acompanhamento nasce LIGADO por corretora (desligue em `acionamento_profile.acompanhamento`).
3. **Publicar as 6 cartas no RAG (não urgente; pode ser no fim).** Passo a passo, no EasyPanel: abrir o serviço **smith-api** → aba **Console** (terminal do contêiner) →
   colar `python scripts/publicar_cartas_0971.py` (mostra o plano, nada grava) → conferir "2 tenants · 6 cartas" → colar `python scripts/publicar_cartas_0971.py --vivo` →
   a saída termina com `VERIFY: 6/6 documentos nos 2 tenants`. Se o console abrir fora de `/app`, antes: `cd /app`. Se der erro de Qdrant, me mande a linha do erro. O
   relatório da SPEC repete estes passos com a saída esperada.
4. **A linha da atendente:** o filtro R11 descarta pessoal/colegas antes de qualquer carta ou régua — nada seu a decidir; só saber que existe.

## 8. GATE FINAL
MUTAÇÃO — a regra: cada mutação declarada (U1…U8, por cópia, medida em subprocesso) deixa VERMELHA uma asserção de NOME NOVO; uma mutação verde reprova o gate.
guarda `test_o_caso_se_explica_sozinho.py` VERDE com PARES · `--mutar` 16/16 por nome · regressão zero nos guardas de atendimento da 086/090/097 · `npm run test:casa` 16/16 ·
régua rodada no acervo com as duas linhas · canário vivo com supressão provada · suíte inteira (árvore parada) · relatório com card · push `git push origin HEAD:main`.
