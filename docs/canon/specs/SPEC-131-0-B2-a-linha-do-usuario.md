modelo: claude-opus-5-5

# SPEC-131-0-B2 — A linha do usuário (fase 1): o corretor conecta o PRÓPRIO WhatsApp e fala com o AutoBrokers na conversa consigo mesmo

> **v1.0 · 14/10/2026** · redator Opus 5.5 · branch `spec/131-0-B2-a-linha-do-usuario` (da `origin/main` depois do push da 132) · AAA v13 ·
> **CRÍTICO**. Fonte: [proposta](../specs-propostas/PROPOSTA-A-LINHA-DO-USUARIO-NO-WHATSAPP.md) · **D-132F-01/02/04/06/08** · D-131-0-11 ·
> [132-C](SPEC-132-C-o-whatsapp-do-corretor.md) (o motor reaproveitado). 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ o corretor toca "Conectar meu WhatsApp" no Meu perfil, lê um QR e, em "Mensagem para você", recebe as boas-vindas;
                 daí escreve, manda áudio, foto, PDF ali e recebe a MESMA resposta do chat principal, marcada "▸ AutoBrokers".
                 Nenhuma outra conversa do aparelho é lida nem guardada. Nada vai a cliente.
RISCO .......... 7 · corretora 2 · SAI DO PRÉDIO 3 (envio + privacidade do aparelho inteiro) · TODO uso 2
SUPERFÍCIE ..... 2 · peça nova sobre peças que existem
PISO ........... CRÍTICO: envia mensagem · lê o aparelho inteiro (LGPD) · identidade pelo pareamento · migration
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · confirmação se houver blocker
O FIO .......... §2 · `backend/tests/test_spec1310b2_o_fio.py` = 1ª entrega da L4, VERMELHO
PARALELISMO .... L1 ‖ L3 (contrato §5) → L2 → L4 costura
GATES .......... fio · 2 corretoras · 6 mutações · outra conversa = 0 bytes gravados · atendimento e QCM intactos · rotas + next start · bateria
O ELO .......... "responde PORQUE o fromMe do próprio chat chega ao webhook" → BLOCO 0 (M1)
FAIXA .......... 💭 6–8 h (BLOCO 0 com o chip ≈ 1 h, com o Founder)
```

## 1. O contrato
**Muda:** uma instância Evolution GO por PESSOA (`purpose='linha_do_usuario'` + `owner_user_id`), pareada no Meu perfil · o desvio no
webhook ANTES do observer · o filtro da conversa consigo mesmo · as boas-vindas · o turno e a saída do motor da 132-C · o estado da linha
na tela · os avisos do sistema pelo WhatsApp **construídos e DESLIGADOS** (D-132F-04).
**Não pode mudar:** o número de ATENDIMENTO · o do QCM · o central "AutoBrokers" da 132-C (pronto, desligado, reserva) · **nada vai ao
CLIENTE** (fase 2, 135) · conversa que não seja a consigo mesmo nunca é gravada, logada nem mandada a modelo.

## 2. O FIO
```
Meu perfil → "Conectar meu WhatsApp" → POST /api/linha-do-usuario/conectar (company_id + user_id da sessão) → pairing_orchestrator
(escopo company+purpose+DONO) → nome_da_instancia(company,'linha_do_usuario',dono) → QR → leitura → evento de conexão → integrations
(número, jid, lid) → boas-vindas à PRÓPRIA conta (id guardado) → "Mensagem para você" → webhook /evolution-go/<token> → desvio ANTES do
observer → entrada: chat = própria conta E fromMe E id NÃO é do
sistema (o resto: descartado sem gravar) → membro DONO → conversa whatsapp_assistente → chat_anexos.preparar → o MESMO /chat/stream em
processo → "▸ AutoBrokers\n…" → cinto único (destino = a própria linha) → envio → id guardado → (cotação) a volta pela MESMA linha
```

## 2.1 BLOCO 0
**📊 Já lido no código (14/10):** o pareamento é por `company_id + purpose` (`pairing_orchestrator.py:460`) e o nome da instância nasce
só em `channel_identity.nome_da_instancia` → o DONO entra nos dois. O cinto da 132-C recusa destino que seja instância do produto → a
conversa consigo mesmo pede exceção exata (destino = a linha que envia). O aviso das 06:45 sai pelo briefing (`renovacao.py:572`,
`DeliveryExecutor`) → os avisos do sistema são um DESTINO dele, nunca publicador novo (§5).

**A medir com o chip (D-132F-06; o Founder pareia — passo a passo no prompt de abertura).** Instância de MEDIÇÃO `ab-lu-medicao` pela API do
Evolution GO, webhook num receptor TEMPORÁRIO do gerente (script local + túnel de uso único) que grava só campos de roteamento (evento,
fromMe, chat mascarado, servidor do JID, id) — nunca texto de outra conversa, nunca serviço de terceiros. Apagada no fim.

| # | premissa | o que muda conforme o resultado |
|---|---|---|
| M1 | a mensagem em "Mensagem para você" chega ao webhook? com JID (`s.whatsapp.net`) e/ou LID (`lid`)? | ambos → casar os dois · só um → casar por ele e guardar o outro quando vier · **não chega → a fase 1 usa o central da 132-C** (D-132F-01, reserva) e a linha fica para a fase 2; registra e segue |
| M2 | a resposta à própria conta aparece no celular? notifica? | sim → como está · sem notificar → a síncrona fica; a cotação ganha 2ª via no painel · não aparece → central |
| M3 | memória/CPU por instância (antes × depois) | → `LINHA_DO_USUARIO_MAX_LINHAS` com folga ≥ 30 % de RAM no KVM2 (P-132D-01); cheio → "estamos no limite de conexões" |
| M4 | 4 aparelhos e 14 dias sem o celular: que evento o GO manda? | o evento → `desconectada` + motivo na tela; 4 ocupados → erro humano antes do QR |
| M5 | o history sync chega ao webhook? o GO guarda mensagens no banco dele? | chega → descartado na entrada · o GO guarda → desligar/apagar; sem como → **PARA** (CLAUDE.md §10, 4) |
| M6 | o envio da API volta como fromMe com o MESMO id? | sim → anti-eco por id · não → por prefixo + hash do enviado nos últimos 10 min |

## 3. Dados — `backend/supabase/migrations/20261015_01_spec1310b2_linha_do_usuario.sql` (expand-only; MIGRATIONS-AUTHORITY antes)
- `integrations` + `owner_user_id uuid null` (FK `users_v2`), `linha_jid`, `linha_lid text null`, `linha_conectada_em`,
  `linha_desconectada_em timestamptz null`, `linha_motivo text null` · CHECK `purpose='linha_do_usuario'` ⇒ dono não nulo · únicos parciais
  `(owner_user_id)` e `(paired_phone_e164)` onde `purpose='linha_do_usuario' and is_active`.
- `linha_mensagens_do_sistema` (integration_id, company_id, message_id, hash_texto, enviada_em): anti-eco DURÁVEL (P-132C-02) · limpeza
  > 7 dias no job que nasce aqui (P-132C-04).
- `linha_avisos_registro` (company_id, user_id, tipo, criado_em, enviado, motivo_nao_enviado): o "teria enviado"; nunca o texto.
- RLS + filtro `company_id` no código · APPLY/VERIFY/ROLLBACK antes; aplica o gerente (`lock_timeout 5s`, nunca `SET SESSION`).

## 4. O desenho
**Meu perfil → Meu WhatsApp** (a seção `MeuWhatsAppDeTrabalho` ganha o bloco de cima): *Não conectado* → **Conectar meu WhatsApp** → "No
celular: WhatsApp → Aparelhos conectados → Conectar um aparelho → aponte para este código" + QR (renova sozinho). Conectado: "✓ Conectado —
{número mascarado} · desde {data} · [Desconectar]". Conectar = número verificado (a posse é o QR; o ATIVAR fica só no central).

**As boas-vindas** (logo após parear; a lista mostra só o que a corretora tem ligado):
```
▸ AutoBrokers
Oi, {primeiro_nome}! Pronto: esta conversa com você mesmo agora é o seu canal direto com o AutoBrokers da {corretora}.

É só escrever aqui, como escreveria para um colega. Você pode pedir:
• *Cotação* — mande a placa, a foto do documento, a apólice atual em PDF ou um áudio contando o que o cliente quer.
• *Dúvidas de seguro* — "a apólice do João cobre vidro?", "o que muda se ele tirar o carro reserva?"
• *Ler um documento* — mande a foto ou o PDF e peça o resumo.
• *O seu dia* — "o que tenho para hoje?", "quais renovações ficaram prontas?"
• *Números da corretora* — "como está a produção do mês?"

Uma resposta leva alguns segundos; uma cotação, de 1 a 2 minutos, e chega aqui mesmo.

Combinados:
• Eu só leio ESTA conversa. As suas outras conversas não são lidas nem guardadas.
• Eu não mando nada para os seus clientes: quem envia é sempre você.
• O que começa com ▸ AutoBrokers sou eu; o resto é você.
• Para desligar: Meu perfil → Meu WhatsApp → Desconectar (ou Aparelhos conectados, no celular).
```
- **Prefixo** "▸ AutoBrokers" + quebra de linha em TODA mensagem do sistema (a conta é a mesma).
- **O assistente:** o motor da 132-C, sem cópia — `turno.py` recebe a origem `linha_do_usuario` e o DONO da linha como identidade; conversa
  `whatsapp_assistente` com `metadata.via='linha_do_usuario'` (fora da Central, do espelho e da Fila); membro de duas corretoras: o "qual
  corretora?" da 132-C, uma vez; teto de turnos = o da 132-C; "digitando…" enquanto pensa.
- **Privacidade:** na entrada, antes de gravar, logar ou chamar: outra conversa, grupo, status, broadcast, newsletter, history sync →
  **descartado**, contando só `descartadas_total` por linha.
- **Desconexão SÓ NA TELA** (D-132F-04): faixa no topo e no Meu perfil — "Seu WhatsApp desconectou do AutoBrokers em {data}. Isso acontece
  quando o celular fica 14 dias sem internet ou quando o aparelho é removido em *Aparelhos conectados*. [Conectar de novo]". Aos 💭 10 dias
  sem sinal do celular: "Abra o WhatsApp no celular para a conexão continuar ativa."
- **Avisos do sistema pelo WhatsApp, prontos e desligados:** destino `linha_do_usuario` no `DeliveryExecutor` (renovações calculadas,
  licença do Agger, falha de conexão; "WhatsApp desconectado" só pelo central). `AVISOS_WHATSAPP_LIGADO` ausente = nada sai e o registro
  anota "teria enviado". Ligar é do Founder, por tipo.
- **Capacidade (D-132F-08):** no KVM2 as linhas moram no MESMO Evolution GO, com o teto da M3; `LINHA_DO_USUARIO_LIGADA` ausente = o
  botão não aparece e o desvio cala. Servidor próprio → antes das pagantes (KVM4).

## 5. Fatias (cada arquivo, UM dono)
| fatia | entrega | arquivos |
|---|---|---|
| **L1 · a linha com dono** | migration · pareamento por pessoa · API · estado · teto | a migration · `backend/app/services/whatsapp/channel_identity.py` · `…/whatsapp/pairing_orchestrator.py` · `backend/app/services/linha_do_usuario/{__init__,pareamento,estado}.py` (NOVOS) · `backend/app/api/linha_do_usuario.py` (NOVO) + router · `backend/tests/test_spec1310b2_pareamento.py` |
| **L2 · entrada e assistente** | desvio, filtro, anti-eco, boas-vindas, turno, saída | `backend/app/services/linha_do_usuario/{entrada,boas_vindas}.py` (NOVOS) · `backend/app/api/webhook.py` (um hunk) · `backend/app/services/atalho/turno.py` · `…/atalho/envio.py` · `backend/tests/test_spec1310b2_entrada.py` |
| **L3 · a tela** | Conectar/QR/estado/Desconectar · faixa | `components/perfil/MinhaLinhaDoWhatsApp.tsx` (NOVO) · `components/perfil/MeuWhatsAppDeTrabalho.tsx` · `components/perfil/useMeuPerfil.ts` · `app/api/dashboard/meu-perfil/linha/**` (NOVO) · `components/avisos/FaixaDaLinha.tsx` (NOVO) + a montagem no layout do dashboard · `tests/linha-do-usuario.test.mjs` |
| **L4 · avisos + costura** | destino desligado, registro, limpeza, o fio | `backend/app/services/linha_do_usuario/avisos.py` (NOVO) · o arquivo do `DeliveryExecutor` (só o destino) · `backend/tests/test_spec1310b2_o_fio.py` |

**Contrato:** L1 exporta `linha_da_instancia(instance_name) -> {integration_id, company_id, owner_user_id, jid, lid} | None`. API:
`POST /api/linha-do-usuario/conectar` → `{tentativa_id, qr}` · `GET …/estado` → `{estado: nao_conectada|aguardando_qr|conectada|
desconectada|limite, numero_mascarado, desde, motivo}` · `POST …/desconectar`. company_id e user_id SEMPRE da sessão.

## 6. A régua
**Mutações (cada uma VERMELHA uma vez; restaura por cópia; nunca muta a árvore de outro agente):** (1) mensagem de OUTRA conversa chega ao
turno, ao banco ou ao log (sonda: 0 bytes em `messages`, logs e Storage) · (2) mensagem do sistema volta como pergunta (com e sem id) ·
(3) a linha de A responde dado de B · (4) ATENDIMENTO ou QCM mudam (`test_spec133a_o_fio`, `test_spec132c_o_fio`; `webhook.py` = um
hunk) · (5) o 2º corretor recebe o QR do 1º · (6) com a chave ausente, um aviso sai.
**Isolamento** com duas corretoras reais. **§9.1:** `test:rotas-montam` + `next start` + `GET /api/linha-do-usuario/estado` (401) + `tsc`.
**Canário:** o chip conectado pela TELA, texto + áudio + PDF + uma Cotação Rápida de teste. **Verba** 💭 ≤ US$ 0,30.

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-1310B2-01 | Uma instância por PESSOA; o dono no escopo do pareamento e no nome | 92 | por corretora 20 |
| D-1310B2-02 | A linha mora na corretora em que foi pareada; membro de duas escolhe uma vez | 85 | na plataforma 60 (a fase 2 envia pela corretora) · uma por corretora 30 (2 dos 4 aparelhos) |
| D-1310B2-03 | Reusar `whatsapp_assistente` com `via` no metadata | 85 | canal novo 60 (todo filtro da Fila teria de aprender) |
| D-1310B2-04 | Anti-eco durável no banco (id + hash) | 90 | só Redis 50 (P-132C-02) |
| D-1310B2-05 | Descartar na entrada, contando só o total | 95 | gravar e filtrar depois 10 |
| D-1310B2-06 | Avisos = destino do briefing, desligados por chave | 90 | módulo novo 25 (publicador paralelo) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://engineering.fb.com/2021/07/14/security/whatsapp-multi-device/** · faz: aparelho vinculado com histórico sincronizado ·
   modelamos: a linha como aparelho da pessoa · rejeitamos: guardar o histórico · juiz: mutação 1.
2. **https://pkg.go.dev/go.mau.fi/whatsmeow/types/events** · faz: `Message` (`IsFromMe`, `Chat`), `HistorySync`, `LoggedOut` ·
   modelamos: "chat = própria conta E fromMe" e `LoggedOut` → estado · rejeitamos: `HistorySync` · juiz: eventos do BLOCO 0 no filtro.
3. **https://pkg.go.dev/go.mau.fi/whatsmeow/types** · faz: a mesma pessoa por JID e por LID · modelamos: casar os dois · rejeitamos: o
   remetente como identidade · juiz: evento só com LID → a linha certa.
4. **https://github.com/EvolutionAPI/evolution-go** · faz: instância, QR, webhook, envio · modelamos: uma instância por pessoa no webhook
   que existe · rejeitamos: outro servidor de WhatsApp · juiz: nenhum cliente HTTP novo de WhatsApp.

## 9. O QUE SAI (com destino)
**Fase 2 — envio a CLIENTES pela linha → 135**, com a D-132F-05: teto por linha **≥ 30/dia** subindo com sinais saudáveis, intervalos
irregulares, horário comercial, "digitando…", 3–5 variações, só quem tem relação, para quando o cliente responde, "não quero receber",
pausa por risco, chave geral. 📊 **A cobrança já tem** (`backend/app/services/platform_outbound.py`,
o governador da SPEC-063): 241–479 s nunca múltiplo de 30 · 12/h · 20/dia novo, 200 maduro · 08–20 h, domingo bloqueado · parada de
emergência · falha FECHADA sem Redis · fila de cortesia · "não quero receber" em `billing_replies.py`. **Falta:** chave por LINHA (hoje
`company_id`) · o mínimo 30 · "digitando…" · variações · parar quando o cliente responde · pausa por não entregue. → a 135 ESTENDE esse
governador (um motor só); 20 → 30 na cobrança é decisão da 135. Servidor próprio das linhas → KVM4 · central oficial → 134.
