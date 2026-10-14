# PROPOSTA — A linha do usuário no WhatsApp (o WhatsApp de cada corretor, pareado no Meu perfil)

> 14/10/2026 · gerente da SPEC-132 · **PROPOSTA para o Founder decidir** (nada executado). 📊 medido · 💭 estimativa.
> Origem: retorno do Founder depois da 132 ("500 corretoras pedindo cotação no mesmo número"; "o corretor parear o próprio
> WhatsApp no Meu perfil e conversar consigo mesmo"; "esse número vai ser usado depois para renovação, cobrança, cotação ao cliente").

## 1. O que existe hoje (FATO)
- **Meu WhatsApp de trabalho (131-B)**: só um NÚMERO digitado + "confirmo". Nada é pareado, nada é enviado por ele. Usos: (a) o botão
  "Quero renovar" da página do cliente abre o WhatsApp DO CLIENTE para esse número; (b) "Enviar pelo WhatsApp" na aba Renovações/Cotações
  abre o `wa.me` no aparelho de quem clicou — quem envia é a pessoa, à mão; (c) 132-C: o "ATIVAR" prova que o número é dela.
- **Número central "AutoBrokers" (132-C)**: pronto e DESLIGADO (`ATALHO_WHATSAPP_LIGADO`); uma instância da plataforma conversa com todos os
  corretores verificados, pelo MESMO turno do chat.

## 2. As opções (nota 0–100, para o produto em escala — 💭 500 corretoras × ~5 usuários)
| # | opção | nota | por quê |
|---|---|---|---|
| 1 | Número central único, não oficial (132-C) | 70 piloto · **35** escala | UX clara (contato separado); 💭 dezenas de milhares de msg/dia num número só → bloqueio derruba TODAS as corretoras de uma vez |
| 2 | Número central na API oficial da Meta | **80** escala · 50 agora | sem bloqueio; custo por resposta (fonte: PASSAGEM 05/10: desde 01/10/2026 ~US$ 0,0068/msg BR, 1.000 grátis/mês/número); barreira de aprovação agora |
| 3 | Um número central POR corretora ("AutoBrokers da Resulta") | 65 | divide o risco, mas é um chip por corretora e continua não oficial |
| 4 | **A linha do usuário**: cada corretor PAREIA o próprio WhatsApp no Meu perfil e conversa com o AutoBrokers na conversa consigo mesmo ("Mensagem para você") | **88** | risco de bloqueio ~0 na conversa consigo mesmo (não há terceiro para denunciar); a posse do número é provada pelo próprio QR; é a MESMA linha que depois envia ao cliente (renovação, cotação, cobrança) — o que o produto precisa de qualquer forma |
| 5 | Linha do usuário + grupo automático | 55 | grupo criado por robô é sinal de automação; a resposta do sistema continua aparecendo como "você"; mais chamadas |
| 6 | **Híbrido = 4 como base + 1 como reserva/avisos da plataforma (e 1 migra para a Meta quando ela vier)** | **90** | o melhor de cada: o dia a dia na linha do usuário; o central só para quem não pareou e para avisos da plataforma |

## 3. A recomendação: a linha do usuário (opção 6)
- **Uma linha por pessoa**: Meu perfil → "Conectar meu WhatsApp" → QR (como o do atendimento) → uma instância Evolution GO com DONO = a pessoa
  (`purpose='linha_do_usuario'`, `owner_user_id`), separada do número de ATENDIMENTO da corretora e do QCM. O número é detectado do pareamento
  (não precisa digitar nem ATIVAR).
- **Boas-vindas** (enviada pela própria linha, na conversa consigo mesmo): 💭 "Oi, {nome}! Esta conversa agora é o seu canal com o AutoBrokers.
  Tudo o que você faz no chat, pode pedir aqui: cotações (mande a apólice, a placa ou um áudio), dúvidas de cobertura, relatórios, renovações do
  dia, avisos da corretora. As mensagens que começam com ▸ AutoBrokers são minhas."
- **O assistente**: o que a pessoa escreve na conversa consigo mesmo → o MESMO turno do chat (o motor da 132-C, `atalho/turno.py`, reaproveitado
  ~90 %) → a resposta volta na mesma conversa, marcada "▸ AutoBrokers". As mensagens que o próprio sistema mandou são reconhecidas pelo id (sem laço).
- **Privacidade (LGPD)**: a linha vê TODAS as conversas do aparelho. Só se processa: a conversa consigo mesmo e (na fase 2) as conversas com
  clientes da carteira. O resto é descartado sem gravar conteúdo (a regra já usada no observer: conversa pessoal não entra).
- **Fase 2 (com a 135)**: a MESMA linha envia ao cliente (renovação, cotação, cobrança) com o **motor de envio humano**: intervalos irregulares
  (💭 40 s–3 min, nunca fixos), horário comercial, "digitando…" proporcional ao tamanho, teto diário por linha com aquecimento (💭 20/dia na 1ª
  semana, sobe conforme as respostas), 3–5 variações por modelo + nome/carro do cliente, só clientes da carteira, para quando o cliente
  responde, respeita "não quero receber", pausa sozinha com sinais de risco (não entregue, bloqueio) e chave geral de desligar.

## 4. O que precisa ser MEDIDO antes de desenhar (BLOCO 0, com um chip de teste)
1. A mensagem que a pessoa escreve na conversa consigo mesmo chega ao webhook do Evolution GO? (com o JID e com o LID novo do WhatsApp)
2. A resposta enviada pela API à própria conta aparece na conversa consigo mesmo do celular, com notificação?
3. Memória e CPU por instância no Evolution GO (💭 dezenas de MB) → quantas linhas por servidor; o servidor de produção caiu em 14/10 por
   memória (P-132D-01): **o Evolution GO das linhas tem de morar num servidor próprio**, com várias máquinas e a instância presa a uma delas.
4. O limite de 4 aparelhos conectados por conta e a desconexão após 14 dias sem o celular: aviso e repareamento simples.

## 5. O número central "AutoBrokers" (o que já está pronto) — usos que valem
Avisos da plataforma ao corretor que não pareou (renovações calculadas de manhã, licença do Agger vencendo, "seu WhatsApp desconectou",
falha de conexão de sistema); o assistente para quem não quer parear; avisos aos administradores das corretoras; mais tarde, na API oficial.
⛔ Não usar para falar com CLIENTE das corretoras (o cliente fala com a corretora dele, nunca com uma marca de fora).

## 6. Como entra na fila
SPEC **131-0 parte B2 · fase 1** (pareamento, boas-vindas, assistente na conversa consigo mesmo, avisos, privacidade, infra separada) →
fase 2 com a 135 (envio ao cliente com o motor de envio humano). Pode rodar em sequência com "A loja de aplicativos" no mesmo chat (arquivos
quase disjuntos: perfil/WhatsApp × galeria/aplicativos).
