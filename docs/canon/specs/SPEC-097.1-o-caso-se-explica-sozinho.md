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
> **v1.0 · 05/09/2026 · protocolo v11.2 + opção B · marcha PADRÃO (compactada: 1 desenhista, 1 builder, painel de 2 lentes + juiz fresco)** ·
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
> E a régua: 📊 sobre os 542 turnos reais do acervo (36 conversas com acionamento), o motor da 097.1 responde com carta ou com estado ≥ 95 % dos
> **turnos de intenção** e manda o resto para humano com o dossiê PÓS — medido por script, com linha de controle (o motor SEM as cartas cai para
> ~40 %, o número que o investigador previu).

---

## 1. O QUE FOI MEDIDO (📊 05/09/2026, `reality-report-0971.md`)

| fato | número | consequência |
|---|---|---|
| O corpus do pedido (Resulta · DDD 48) é uma linha ADMINISTRATIVA | 84 conversas: cobrança 60 · apólice 50 · cancelamento 22 · **acionamento reconhecível em 4** | 🔴 a linha de sinistro/assistência, onde o acionamento acontece, está no tenant **AutoFleet** (448 conversas, 448 telefones distintos, DDDs do país inteiro, 100 % espelho do Atlas — real, não simulação; a outra atendente aparece em 78 delas). Corpus adotado: 532 conversas / 24.896 mensagens → **36 com acionamento**, 1.088 mensagens do cliente depois dele |
| `role='assistant'` nesse acervo é a ATENDENTE HUMANA | 100 % `payload.origem='espelho'`, `sender_user_id` NULL | não há uma mensagem de IA no pós-acionamento: a 097.1 é construção, não correção |
| A mensagem não é a unidade | 56,3 % ≤ 24 caracteres · 18,5 % com `?` · **542 turnos a 2,01 msgs** | R1: o classificador lê o TURNO (rajada sem resposta no meio) |
| 62 % do tráfego pós-acionamento não é do segurado | parceiro/oficina 673 msgs · segurado 254 · indefinido 161 | R2: o estado responde a quem perguntar; o agente não presume que fala com o segurado |
| Taxonomia por intenção (375 msgs com intenção) | documentos 33 % · agenda 11 % · valores 7 % · oficina 7 % · peça 4 % · carro reserva 2 % · status 3 % · prestador não chegou 3 msgs | 64 % é LOGÍSTICA de reparo, não emergência; regra (D/E/F/C) = 7,5 % do volume; estado (A/B/H/G/J) = 17 % |
| O humano já é excelente | mediana 0,8 min · p90 57,5 min · 1,8 % dos turnos sem resposta | R7: é o PISO; nada da 097.1 pode piorar |
| O caso dura | 6,9 dias · 4,2 episódios · 85 msgs (medianas) · 70× a conversa comum | o caso não cabe numa sessão: o estado tem de ser ESCRITO |
| Hoje no produto | Follow-up não instalado (0/2), `trigger_type='manual'`, sem gatilho · `routines` = 1 linha inativa · agentes `is_active=false`, prompts só de abertura · `work_waits` 0 linhas · `human_handoff_reason` NULL 725/729 · `_TITULOS` sem PÓS · `_o_que_fazer` default "conclua o acionamento" | U1–U3 |
| RAG | `knowledge_cards` 18.715 (global, `source_document_id` NULL em 100 %) · `documents`: Resulta 10, **AutoFleet 0** | as cartas nascem como DOCUMENTOS DO TENANT nos dois tenants; a procedência das 18 mil vai para pendência |
| Markdown no WhatsApp | 222 msgs em 60 conversas com `**`, 47 com `##` | fora do escopo → P-097.1-MARKDOWN-NO-CANAL (R11 da 097 no canal) |

---

## 2. REGRAS

- **R1 · A unidade é o TURNO.** O classificador do pós-acionamento recebe a rajada de mensagens do cliente sem resposta entre elas (janela medida no acervo), nunca uma mensagem solta. 📊 542 ≠ 1.088.
- **R2 · O estado responde a quem perguntar.** Segurado, corretor parceiro ou oficina recebem a mesma verdade escrita ("esperando a loja desde …"). O agente não presume interlocutor; identifica-o pelo que está na conversa, e na dúvida responde sem nomear papel.
- **R3 · Só se afirma o que está ESCRITO.** Previsão, protocolo, valor, autorização e "já está quase" vêm de `work_waits`/`attendance_sessions`/ficha — nunca do modelo. Sem estado novo, a resposta honesta é "não houve novidade; a corretora está cobrando" (carta C3). Nunca prometer prazo que a seguradora não deu.
- **R4 · A espera é escrita por quem sabe dela.** O corredor (`dispatch_router`) abre `work_waits` `esperando_seguradora` quando o acionamento entrega protocolo/previsão (`captured`/`monitoring`/`encaminhado`), com `vence_em` = previsão informada ou o prazo configurado da corretora; abre `esperando_cliente` quando pede documento; e SATISFAZ a espera quando o estado muda ou quando `marcar_fim` grava o desfecho. **Um escritor por estado, nos escritores existentes; nenhum motor novo (§5).** Nada de dedução por silêncio.
- **R5 · O handoff diz PÓS.** Caso já acionado que vai para humano recebe título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>`, `Quem fala`, `O que ele quer`, `Onde parou` (de quem se espera, desde quando), `Falta`, `O que fazer`. **Proibido** "conclua o acionamento" em caso acionado. E `human_handoff_reason` é GRAVADO (o escritor existe e nunca rodou).
- **R6 · Linguagem de corretora (R11 da 097).** As cartas e o dossiê não têm chave, variável, nome de campo, nem linguagem de apólice; terminam numa próxima ação com dono.
- **R7 · Piso humano.** Nenhum guarda da 097.1 passa se a cadência humana medida (mediana 0,8 min, 1,8 % sem resposta) puder piorar por efeito da SPEC: o agente NÃO responde por cima de conversa assumida (`pausar_ia`, 097) e o Follow-up NÃO envia sozinho (`requires_human_approval=true`, `dry_run=true`).
- **R8 · A meta é medida em turnos de intenção.** A régua exclui social (M), mídia sem texto (Z) e fragmentos sem intenção (N); conta resolvido = respondido com carta ou com estado escrito; não resolvido = foi para humano. Linha de controle: a mesma régua sem as cartas.

---

## 3. UNIDADES

### U1 · O estado existe (R4)
- **U1.1** `dispatch_router`: ao gravar `captured`/`monitoring`/`encaminhado` com protocolo ou previsão, abre `work_waits(kind='esperando_seguradora', scope=episódio, vence_em, conversation_id, work_run_id)` pelo helper existente (`_abrir_espera_do_travamento`, que já aceita `vence_em` como argumento — basta passar a previsão; generalizado, não copiado). Ao pedir documento ao cliente (`slot` de documento), `esperando_cliente`.
- **U1.2** satisfação: novo estado do corredor, mensagem do cliente com documento (para `esperando_cliente`), ou `marcar_fim` → `status='satisfeito'`, `satisfeito_por`, `satisfeito_em`. `pausar_ia`/claim não mexem na espera.
- **U1.3** `projetarCasos` (097) já lê `work_waits`: a Fila e o Caso passam a mostrar "esperando a seguradora · Nd" com `fonte_id` real. Sem mudança de tela além do que a 097 já faz.

### U2 · O handoff diz PÓS (R5)
- **U2.1** `human_handoff.py`: título `🔁 PÓS-ACIONAMENTO · <SERVIÇO>` quando o caso tem acionamento (dispatch_state ∈ captured/monitoring/encaminhado ou `work_waits` ativa); `_o_que_fazer` específico (cobrar a seguradora/loja; pedir documento; reagendar); `Onde parou` lê a espera; `Quem fala` lê a heurística de interlocutor (R2) com "indefinido" honesto.
- **U2.2** `human_handoff_reason` gravado no ponto de handoff (o escritor existe: conferir por que nunca rodou — 📊 725/729 NULL — e ligar o caminho real, não um paralelo).

### U3 · O agente responde com regra e com estado (R3, R6)
- **U3.1** as seis cartas C1–C6 (`reality-report-0971.md` §3.1) entram como DOCUMENTOS do tenant (Resulta e AutoFleet) pela ingestão existente (`documents` → cartas), com `ramo`/`temas` de pós-acionamento — nunca um índice paralelo.
- **U3.2** seção "PÓS-ACIONAMENTO" no prompt base de atendimento (código, não linha do banco por tenant): as regras R2/R3, o mapa intenção → carta, e "quando não há estado, diga que não há e que a corretora cobra". Sem alterar o fluxo de ABERTURA (regressão zero no corredor).
- **U3.3** Follow-up `follow-up-whatsapp`: instruções (a), (b), (c) do §3.2 do relatório no template (data migration idempotente em `auxiliary_templates.default_config`/prompt), `dry_run=true` mantido. 🔴 O GATILHO de silêncio (X horas sem mensagem da corretora) fica FORA: não existe motor de Rotina rodando (📊 `routines` 1 linha inativa, `last_run_at` NULL 4/4) e criá-lo aqui seria motor paralelo → **P-097.1-GATILHO-DO-FOLLOW-UP**.

### U4 · A régua da meta (R8)
- **U4.1** `backend/scripts/regua_0971.py` (só SELECT, zero PII na saída): reconstrói os turnos do acervo (regra §0.4 do relatório, MESMO motor), classifica por intenção, passa cada turno pelo classificador/mapa de cartas REAL da U3.2 e pelo estado que a U1 escreveria, e imprime: turnos de intenção · resolvidos por carta · resolvidos por estado · para humano (com título PÓS) · **% resolvido** · linha de CONTROLE sem cartas.
- **U4.2** o número vai ao relatório com 📊; se ficar abaixo de 95 %, a SPEC não mente: diz o número e o que falta (§6).

### E · Canário (Amandus → Resulta → AutoFleet, sem mensagem)
`backend/scripts/canario_0971.py --vivo` (`AUTOBROKERS_CANARIO=1`): episódio canário na Resulta → o corredor dublê grava `captured` com previsão → `work_waits` ativa com `vence_em` e corretora → a projeção da 097 mostra "esperando a seguradora" com `fonte_id` (CONTROLE: antes da escrita, `esperando: null`) → handoff dublê gera o dossiê com `🔁 PÓS-ACIONAMENTO` e `human_handoff_reason` gravado (CONTROLE: caso sem acionamento gera o título antigo) → `marcar_fim` satisfaz a espera → limpeza 0/0/0 por id e corretora.

### G · Guardas (desenhista escreve antes; gate zero VERMELHO em cópia limpa)
- `backend/tests/test_o_caso_se_explica_sozinho.py`: [A] o corredor abre a espera ao capturar (motor real, dublê de banco) e NÃO abre sem protocolo/previsão (controle) · [B] `marcar_fim` satisfaz a espera · [C] o dossiê de um caso acionado tem o título PÓS, `Onde parou` e nunca "conclua o acionamento" (um caso histórico anonimizado: o dossiê antigo fica VERMELHO) · [D] `human_handoff_reason` é gravado · [E] o prompt base tem a seção e o fluxo de abertura é IDÊNTICO (hash do trecho) · [F] as 6 cartas passam pelo guarda de linguagem humana da 097 (`[13]`: sem chave, sem `@N`, sem snake_case) · [G] a régua reproduz ≥ 3 números do §1 e a linha de controle sem cartas dá menos que com cartas · [H] Follow-up: `requires_human_approval` e `dry_run` continuam `true` depois da data migration (mutação: virar `false` fica VERMELHO) · [I] nada de motor novo (`grep` por scheduler/cron/listener novos = zero).
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
P-097.1-GATILHO-DO-FOLLOW-UP · P-097.1-MIDIA-SEM-TEXTO · P-097.1-MARKDOWN-NO-CANAL · P-097.1-CARTAS-SEM-PROCEDENCIA · P-097.1-RAG-AUTOFLEET-VAZIO (📊 0 documentos onde o pós-acionamento acontece; as 6 cartas são o primeiro) · P-097.1-LINHA-COMPARTILHADA (decisão).

## 7. A CAIXA DO FOUNDER
1. 🔴 A linha de acionamento vive no tenant **AutoFleet** (espelho do WhatsApp da segunda atendente), não na Resulta/DDD 48: confirme que é isso mesmo — e que as cartas devem nascer nos DOIS tenants (é o que a SPEC faz).
2. Quando religar o WhatsApp: os agentes seguem `is_active=false` até você ligar; o Follow-up segue `dry_run=true` (rascunho, aprovação humana).
3. Decidir sobre a linha compartilhada (caso + colegas + pessoal no mesmo número) antes de ligar IA num número de atendente real.
4. O gatilho automático do Follow-up depende de Rotinas rodarem (SPEC-058) — hoje nenhuma roda.
