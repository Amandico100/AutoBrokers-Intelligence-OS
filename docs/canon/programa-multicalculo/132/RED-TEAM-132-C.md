# RED TEAM — SPEC-132-C (o WhatsApp do corretor como atalho do chat)

modelo: claude-opus-5-5 · 14/10/2026 · branch `spec/132-o-chat-e-a-cotacao` · HEAD `618ba14` (o atalho não muda desde `26b1fb8`)
Rito: AAA v13 · red team cego ao juiz · READ-ONLY no código.

**Reprodução:** `scratchpad/rt132c/test_rt132c.py` (18 ataques, sobre a fixture `fio` do próprio repositório:
webhook REAL → `atalho.entrada` REAL → `verificacao` REAL → `/chat/stream` REAL, com banco, Redis, Storage, envio e
grafo dublados, rede fechada). Comando:

```
cd backend && bash pesado.sh .venv/Scripts/python.exe -m pytest <scratchpad>/rt132c/test_rt132c.py -q -p no:cacheprovider -s -W ignore
→ 18 passed in 13.28s   (os testes IMPRIMEM o que aconteceu; "passou" = o ataque rodou, não que o produto resistiu)
```

## VEREDITO: QUEBREI uma coisa (1 blocker pequeno). O resto aguentou.

A identidade, a verificação, o isolamento entre corretoras, o anti-laço na ENTRADA, o pareamento e os logs aguentaram.
A quebra está na SAÍDA: a volta da cotação não passa pelo anti-laço.

---

## BLOCKER

### RT-132C-01 · A volta da cotação manda mensagem para o número de uma INSTÂNCIA do produto (robô→robô, 1ª perna)

- **Teste do produto:** SIM. O resumo da cotação chega à linha de atendimento/observer da corretora como se fosse um
  CLIENTE falando com ela (o observer consome; o atendimento pode responder ao número do AutoBrokers).
- **Onde:** `backend/app/services/atalho/envio.py:325-343` (`enviar_ao_membro`) e `:271-303` (`enviar`). Nenhum dos dois
  chama `entrada.numero_do_produto`. O anti-laço só existe na ENTRADA (`entrada.py:278`).
- **Como se chega lá:** o membro verifica o número P (o celular dele). DEPOIS a corretora pareia P como linha de
  atendimento/observer. Isso é comum em corretora pequena: o celular do corretor É o WhatsApp da corretora. Outro caminho:
  o pareamento ainda não gravou `paired_phone_e164` na hora do ATIVAR. Daí em diante, as mensagens que P manda ao assistente
  são ignoradas (certo), mas `cotacao.workflow.gravar_mensagem` → `avisar_pelo_atalho_sem_esperar` → `enviar_ao_membro`
  continua mandando para P. A fixture do repositório já tem esse membro (U5, "verificou o número que é a LINHA da
  corretora"). Os testes só provam a entrada dele.
- **Reprodução** (`test_C2_volta_da_cotacao_vai_para_linha_de_corretora`):
  ```
  C2 volta da cotacao de U5 -> True [('0000', 'int-assistente')] (linha da Alfa termina em 0000 )
  C2 a linha da Alfa recebendo do assistente -> taps: ['int-alfa'] pipeline: []
  ```
  O assistente mandou a mensagem à linha da Alfa, e o observer da Alfa a CONSUMIU como um contato.
- **Conserto (1 linha + 1 teste):** em `enviar` (o cinto único da saída), recusar o destino quando
  `entrada.numero_do_produto(db, tel)` for True. Isso vale para a volta, para o teto, para a pergunta e para o "Pronto".
  A guarda tem de ficar VERMELHA com U5 e verde com U1.

---

## PENDÊNCIAS (o teste do produto não fecha hoje, ou é risco e não defeito medido)

| # | achado | medição | peso |
|---|---|---|---|
| P1 | **O código não é amarrado ao número declarado, e não há teto GLOBAL de tentativas.** O teto é 5 erradas/h POR telefone. Com 12 números saíram 60 palpites sem bloqueio, e o 13º número que acertou virou a identidade do membro. Um código que acerta (ou vaza num print) dá: (a) o chat da corretora como aquele membro; (b) o número do atacante passa a ser o `whatsapp_trabalho_e164` **confirmado**, e o "Quero renovar" (`multicalculo/proposta.py:1240-1270`) usa esse número com o cliente. 💭 Risco por palpite = códigos ativos ÷ 10⁶. | B1: `palpites errados aceitos sem bloqueio global: 60` · `acerto de numero novo -> True · U3 agora: 9999`. B2: `codigo de U4 enviado de OUTRO numero -> True · numero de U4 agora termina em 9999 (era 0004) confirmado_em reescrito: True` | ESSENCIAL |
| P2 | **O teto de 200/dia não conta o que sai fora do turno.** A pergunta "qual corretora?" vai a CADA mensagem (a SPEC diz "uma vez"). A frase "sem agente" vai a cada mensagem e o contador fica em 0. As duas mandam sem limite pelo número da plataforma, e esse número é um só para todas as corretoras: se ele for banido, o atalho cai para todas. | D1: `8 mensagens sem escolher -> perguntas enviadas: 8 · mensagens gravadas: 0`. D2: `10 mensagens sem agente CORE -> respostas: 10 · contador do teto: 0` | VALIOSA |
| P3 | Sem Redis, "trocar corretora" não troca: o "2" cai como TEXTO no chat da corretora da conversa ativa. Não vaza dado (é a mesma pessoa), mas a escolha se perde. | D3: `ultimo turno foi para: ALFA · conteudo do ultimo turno: ['2']` | VALIOSA |
| P4 | `data.key` vindo como lista dá 500 no webhook do assistente (`entrada.filtrar:121` faz `.get` numa lista). Fica fora do `try` do turno. O QCM continua respondendo 200 depois. O JSON quebrado também dá 500, mas isso já existia. | E1: `key_lista -> 500` · `depois do fuzz, o QCM -> 200` | FUTURA |
| P5 | O texto não tem corte antes do turno: 1 MB de texto viraram `chatInput` (custo de modelo). 💭 O WhatsApp limita a mensagem a ~65 mil caracteres, então o risco real é menor. | E1: `texto_1MB -> accepted` (o turno rodou) | FUTURA |
| P6 | 💭 INFERÊNCIA, não medida: (a) `avisar_pelo_atalho_sem_esperar` roda `asyncio.run` com teto de 60 s DENTRO da thread que grava a cotação, e cada mensagem do run espera o WhatsApp; (b) o webhook GO tem limite de `240/minute` por IP (`webhook.py:2888`), e esse IP é o mesmo servidor Evolution para todas as linhas: o tráfego do assistente passa a competir com o atendimento das corretoras; (c) o código em dígitos unicode (`１２３４５６`, `١٢٣٤٥٦`) casa a regex mas nunca o hash, então gasta uma tentativa do dono. | B4: `fullwidth -> '１２３４５６'`, `arabe -> '١٢٣٤٥٦'` | FUTURA |

---

## O QUE AGUENTOU (está bom; a medição está colada)

- **Falsificar identidade:** `Sender`, `participant` ou `sender` diferentes do `remoteJid` não mudam quem fala. A identidade
  é o `Chat`/`remoteJid`, que vem do servidor WhatsApp. Se o atacante não tem o token do webhook, ele não forja.
  A1: `enviados: 0 grafo: 0` · A2: `grafo: 0`.
- **LID:** sem alternativo, cala (`atalho_lid_sem_telefone`). Com `SenderAlt`, usa o telefone alternativo (A3). Sem o 9º
  dígito, reconhece o mesmo membro (A4).
- **Roubar a verificação:** o código vencido recusa, o 2º uso recusa (mesmo vindo de outro número) e o código anterior
  fica invalidado quando se pede um novo (B3). Caracteres zero-width, texto junto e 7 dígitos não casam (B4).
  O ATIVAR vindo da linha de outra corretora é calado e não verifica ninguém (B5).
- **Ler dado de outra corretora:** o `companyId`/`userId` do turno vem do membro verificado, nunca do texto
  (`turno.py:479-490`). O `/chat/stream` reconfere a dona da conversa (`chat.py` "conversa_de_outra_corretora").
  A volta da cotação pedida com a corretora errada não manda nada (C3: `False novos envios: 0`). ⚠️ Prompt injection no
  modelo real NÃO foi medida (o grafo é dublê), mas a superfície é a mesma do chat do painel.
- **Laço:** a mensagem do próprio assistente e a do QCM ao assistente: `enviados: 0`. O QCM reconhece o assistente como
  robô (`numero_de_corretora(ASSISTENTE) = True`) (C1).
- **Parear "assistente" numa corretora comum:** `assistente_so_na_plataforma`. Na empresa da plataforma, é aceito (F1).
  As rotas do hub e do admin fixam o `purpose`, que nunca vem do pedido.
- **Segredo em log:** o código, o segredo do HMAC, os telefones (com e sem 55) e o conteúdo: nenhum aparece no log em
  nível DEBUG (G1: todos `False`).

## CONFIANÇA e o que ficou por medir

Confiança alta no que foi medido (18 ataques rodados no motor real). Ficou por medir: o modelo real sob prompt injection,
o Evolution GO real (formato do LID e de `SenderAlt` ao vivo), o banco real (corrida do índice único), e a mídia enorme
pelo download real (o `_download_media` já existia e corta em `_max_bytes()` só depois de ler a resposta inteira).

## NOTA: 82 / 100
O desenho é sólido e o fio aguenta. Perde pontos pela saída sem anti-laço (o blocker) e pela verificação, que não amarra
o código ao número declarado e não tem teto global.
