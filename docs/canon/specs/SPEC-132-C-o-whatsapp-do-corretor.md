# SPEC-132-C — O WhatsApp do corretor: o mesmo chat principal, pelo WhatsApp dele (o atalho)

> **v1.0 · 14/10/2026** · gerente Opus 5.5 · branch `spec/132-o-chat-e-a-cotacao` · rito AAA v13.2 · **CRÍTICO** (envia mensagem).
> Fonte: pedido do Founder de 14/10 · D-131-0-11 (o WhatsApp do membro em DOIS usos: PEDIR pelo número verificado, conversando com o
> número do AutoBrokers · NEGOCIAR pela instância dele, com a 135) · SPEC-131-0 proposta V25/V37 (B1) · D-131-43 (Meu WhatsApp de
> trabalho = número confirmado) · as frentes do BLOCO 0 da 132. 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ o corretor salva o contato "AutoBrokers" no celular e conversa com ele como conversa com o chat principal: escreve,
                 manda áudio, foto, PDF da apólice — e recebe a mesma resposta (inclusive a Cotação Rápida: o resumo e o link da
                 apresentação). Nada muda no número de ATENDIMENTO da corretora nem no do Quem Cobra Menos.
RISCO .......... 7 · corretora 2 · SAI DO PRÉDIO 3 (mensagem enviada) · TODO uso 2
SUPERFÍCIE ..... 2 · peça nova sobre peças que existem (webhook Evolution GO, empresa da plataforma, turno do CORE, chat_anexos)
PISO ........... CRÍTICO: envia mensagem · identidade por telefone (quem é quem) · company_id escolhido pelo NÚMERO
NÍVEL .......... CRÍTICO · builders Opus 5.5 · juiz ‖ red team · confirmação se houver blocker
O FIO .......... §2 · `backend/tests/test_spec132c_o_fio.py`
GATES .......... fio · 2 corretoras · número desconhecido = silêncio · anti-laço · mutações · rotas montam · bateria
FAIXA .......... 💭 5–7 h
```

## 1. O contrato
**Muda:** um número da PLATAFORMA "AutoBrokers" (instância Evolution GO própria, `integrations.purpose='assistente'`, na empresa da
plataforma que já existe para o canal) · a VERIFICAÇÃO do "Meu WhatsApp de trabalho" por posse (a pessoa MANDA um código do celular
dela para o número do AutoBrokers) · o desvio no webhook para esse número, ANTES do observer, como o do QCM · o turno do CORE para quem
fala por ali (a MESMA conversa/engine do chat: `conversations` com `channel='whatsapp'`, `user_id` = o membro) · a resposta pelo mesmo
número (texto em formato WhatsApp; o link da apresentação vai como texto) · o resultado da Cotação Rápida volta também pelo WhatsApp
quando a conversa nasceu nele.
**Não pode mudar:** o número de ATENDIMENTO da corretora (observer/attendance) · o número do QCM (`canal_convidados`, `entrada.turno`)
· a regra "o produto não envia nada ao CLIENTE" (aqui o produto responde ao PRÓPRIO corretor verificado) · número não verificado nunca
vira identidade (D-131-0 V37).

## 2. O FIO
```
Meu perfil → "Usar o AutoBrokers pelo WhatsApp" → código de 6 dígitos (hash, 15 min, uso único) + botão wa.me/<número do AutoBrokers>
?text=ATIVAR 123456 → o corretor envia do CELULAR DELE → webhook /evolution-go/<token> → integração purpose='assistente' →
desvio ANTES do observer → "ATIVAR 123456" casa o código → grava o número do remetente no membro (verificado_em) → responde
"Pronto, {nome}…" → mensagem seguinte do mesmo número → membro verificado (1 corretora; >1 → pergunta qual, uma vez) → conversa do
canal → anexos (mídia → Storage → chat_anexos.preparar) → turno do CORE (mesma engine do /chat/stream, sem stream) → texto formatado
→ envio pela instância do AutoBrokers → (cotação) o Work Run `cotacao.chat` grava em `messages` E envia pelo WhatsApp
```

## 2.1 BLOCO 0 (14/10/2026)
| # | premissa | estado | o que muda |
|---|---|---|---|
| W1 | existe número da plataforma? | 📊 empresa `company_kind='platform_canal'` (migration `20261005_01`) com a integração do QCM; desvio no webhook antes do observer (`webhook.py:2896-2936`) | nova integração `purpose='assistente'` na MESMA empresa da plataforma, outro número (chip novo — 🧑 Founder) |
| W2 | identidade por telefone | 📊 `company_members.whatsapp_trabalho_e164` confirmado por CLIQUE (`perfil_do_membro.py:161-178`); 0 verificação por posse | `whatsapp_trabalho_verificado_em` (coluna nova) só pelo código enviado do próprio celular |
| W3 | anti-laço | 📊 `numero_de_corretora` (`canal/repositorio.py:186-209`) lê `paired_phone_e164` e `human_support_destinations` | o assistente ignora fromMe, grupo, e números de instâncias do produto |
| W4 | turno sem stream | 📊 `/chat` (não stream) existe; `stream_agent_eventos` (`graph.py:2514`) | reusar a engine coletando o texto; nunca outro agente |
| W5 | mídia | 📊 o QCM recebe mídia como texto extraído; `chat_anexos.preparar` (132-A) lê bytes do Storage | a mídia do WhatsApp sobe ao Storage no prefixo da corretora do membro e passa pelo `preparar` |

## 3. Dados — migration `20261014_03_spec132c_atalho_whatsapp.sql` (expand-only)
`company_members.whatsapp_trabalho_verificado_em timestamptz null` · tabela `whatsapp_atalho_codigos` (company_id, user_id, hash do
código, expira_em, usado_em; índice único parcial por membro ativo) com RLS + filtro no código · `integrations.purpose` aceita
`'assistente'` (se houver CHECK) · índice único: um número verificado ↔ um membro por corretora.

## 4. O desenho
- **Meu perfil → Meu WhatsApp de trabalho:** estado "Confirmado" vira "Verificado ✓ — você pode falar com o AutoBrokers pelo WhatsApp";
  botão "Usar pelo WhatsApp" abre o passo: "Salve o contato AutoBrokers e mande a mensagem abaixo do SEU celular" + [Abrir no WhatsApp]
  + o código visível + "Expira em 15 minutos".
- **No WhatsApp:** respostas curtas, *negrito* do WhatsApp, listas simples, link no fim; áudio é transcrito; foto/PDF lidos; "digitando…"
  enquanto pensa (a presença já existe). Número desconhecido: SILÊNCIO (sem resposta, sem registro de conteúdo). Teto 💭 200 msg/dia/membro.
- **Admin (portal da plataforma):** Conexões → Canais ganha o número "AutoBrokers (assistente dos corretores)" com o QR, como o do QCM.

## 5. Fatias
| fatia | entrega | arquivos |
|---|---|---|
| **C1 · a verificação** | código, wa.me, tela, gravação por posse | migration · `backend/app/services/perfil_do_membro.py` · `backend/app/services/atalho/verificacao.py` (NOVO) · `components/perfil/MeuWhatsAppDeTrabalho.tsx` · `app/api/dashboard/meu-perfil/**` · testes |
| **C2 · o atalho** | desvio no webhook, turno do CORE, resposta, mídia, teto, silêncio | `backend/app/services/atalho/*` (NOVOS: entrada, turno, envio) · `backend/app/api/webhook.py` (só o desvio) · testes |
| **C3 · costura** | o resultado da cotação pelo WhatsApp, o QR no admin, o fio | `backend/app/services/cotacao/workflow.py` (só o envio pelo canal) · a tela de Canais do admin · `test_spec132c_o_fio.py` |

## 6. A régua
Mutações (cada mutação VERMELHA uma vez): (1) número NÃO verificado é atendido · (2) código usado 2× · (3) código de A vincula membro de B · (4) mensagem do número do
ATENDIMENTO ou do QCM cai no assistente · (5) fromMe/grupo gera resposta · (6) membro de duas corretoras recebe dado da outra.
Isolamento com duas corretoras. Canário: depois do QR do Founder (caixa do Founder), uma conversa real com o número do gerente.

## 7. Decisões
| # | decisão | nota | contra |
|---|---|---|---|
| D-132C-01 | Um número da PLATAFORMA "AutoBrokers" para todos os corretores de todas as corretoras (identidade pelo número verificado) | 88 | o número de atendimento da corretora 30 (confunde e o observer consome) · grupo por corretor 40 · o número do QCM 35 (marca isenta, outro público) · parear o WhatsApp de cada corretor já 55 (é a 135/B2) |
| D-132C-02 | Verificação por POSSE: a pessoa envia o código do próprio celular (nada é enviado a ela antes) | 90 | código enviado pelo produto 70 (manda mensagem a número não provado) |
| D-132C-03 | Número desconhecido = silêncio | 85 | responder "número exclusivo de corretores" 60 (vira alvo de spam) |
| D-132C-04 | O mesmo agente CORE e a mesma conversa do chat; só o canal muda | 92 | um agente novo 20 (motor paralelo, CLAUDE.md §5) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages** · faz: mensagens de texto/mídia e o formato
   WhatsApp · modelamos: respostas curtas com link no fim · rejeitamos: template pago (aqui é Evolution) · juiz: confere o texto enviado.
2. **https://faq.whatsapp.com/5913398998672934** (click-to-chat `wa.me`) · faz: abre a conversa com o texto pronto · modelamos: o
   "ATIVAR 123456" pré-preenchido · rejeitamos: QR do código · juiz: abre o link e confere o texto.
3. **https://www.twilio.com/docs/verify** · faz: verificação de posse de telefone com código, expiração e tentativas · modelamos:
   hash, 15 min, uso único, teto de tentativas · rejeitamos: SMS (custo) · juiz: tenta o código 2× e depois de vencido.

## 9. O QUE SAIU
O WhatsApp de CADA corretor pareado para falar com CLIENTES e negociar → 135 (B2) · vários números de assistente por corretora (marca
própria) → pendência · voz em tempo real → pendência.
